#!/usr/bin/env python3
"""
CLI wrapper for UTR-LM 5'UTR expression/stability prediction.
Takes a FASTA of 5'UTR sequences, predicts MRL (mean ribosome loading),
TE (translation efficiency), or EL (expression level).
"""

import argparse
import glob
import os
import sys

import numpy as np
import torch
import torch.nn as nn
from esm.data import Alphabet, FastaBatchedDataset
from esm.model.esm2_secondarystructure import ESM2 as ESM2_SISS
from esm.model.esm2_supervised import ESM2 as ESM2_SI

LAYERS = 6
HEADS = 16
EMBED_DIM = 128
BATCH_TOKS = 4096


class CNNLinear(nn.Module):
    """Downstream predictor: ESM2 backbone + FC head."""

    def __init__(self, esm2_cls, alphabet, nodes=40, dropout3=0.5, inp_len=50):
        super().__init__()
        self.inp_len = inp_len
        self.esm2 = esm2_cls(
            num_layers=LAYERS,
            embed_dim=EMBED_DIM,
            attention_heads=HEADS,
            alphabet=alphabet,
        )
        self.dropout3 = nn.Dropout(dropout3)
        self.relu = nn.ReLU()
        self.flatten = nn.Flatten()
        self.fc = nn.Linear(in_features=EMBED_DIM, out_features=nodes)
        self.output = nn.Linear(in_features=nodes, out_features=1)

    def forward(self, tokens):
        x = self.esm2(
            tokens,
            [LAYERS],
            need_head_weights=False,
            return_contacts=False,
            return_representation=True,
        )
        # BOS/CLS token embedding
        x = x["representations"][LAYERS][:, 0]
        x_o = x.unsqueeze(2)
        x = self.flatten(x_o)
        o_linear = self.fc(x)
        o_relu = self.relu(o_linear)
        o_dropout = self.dropout3(o_relu)
        o = self.output(o_dropout)
        return o


def parse_fasta(path):
    """Parse a FASTA file, yielding (header, sequence) tuples."""
    header, seq_parts = None, []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(seq_parts)
                header = line[1:]
                seq_parts = []
            elif line:
                seq_parts.append(line)
    if header is not None:
        yield header, "".join(seq_parts)


def find_checkpoint(model_dir, task, cell_line=None, fold=0):
    """Find the appropriate checkpoint file."""
    if task == "mrl":
        pattern = os.path.join(model_dir, "Downstream", "MRL", f"MJ3_*_fold{fold}_*.pt")
    else:
        task_prefix = "TE" if task == "te" else "EL"
        label = "te_log" if task == "te" else "rnaseq_log"
        pattern = os.path.join(
            model_dir,
            "Downstream",
            "TE_EL",
            f"MJ4_*_{task_prefix}_*_{cell_line}_{label}_*_finetuneTrue_*_fold{fold}_*.pt",
        )
    matches = glob.glob(pattern)
    if not matches:
        print(f"Error: no checkpoint found for pattern {pattern}", file=sys.stderr)
        sys.exit(1)
    return matches[0]


def main():
    parser = argparse.ArgumentParser(
        description="Predict 5'UTR expression metrics with UTR-LM"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="FASTA file of 5'UTR DNA sequences"
    )
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--task",
        default="mrl",
        choices=["mrl", "te", "el"],
        help="Prediction task: mrl (mean ribosome loading), te (translation efficiency), "
        "el (expression level). Default: mrl",
    )
    parser.add_argument(
        "--cell-line",
        default="HEK",
        choices=["HEK", "pc3", "Muscle"],
        help="Cell line for TE/EL tasks (default: HEK)",
    )
    parser.add_argument(
        "--model-dir",
        default="/opt/utrlm/Model",
        help="Path to Model directory",
    )
    parser.add_argument(
        "--folds",
        default="0",
        help="Comma-separated fold indices to ensemble (default: 0). Use 'all' for 0-9.",
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help="Path to a fine-tuned checkpoint (.pt) to use instead of bundled weights",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)

    # Determine task parameters
    if args.task == "mrl":
        esm2_cls = ESM2_SISS
        inp_len = 50
        dropout3 = 0.5
    else:
        esm2_cls = ESM2_SI
        inp_len = 100
        dropout3 = 0.2

    # Parse fold indices
    if args.folds == "all":
        fold_indices = list(range(10))
    else:
        fold_indices = [int(x) for x in args.folds.split(",")]

    alphabet = Alphabet(standard_toks="AGCT", mask_prob=0.0)

    # Load sequences
    sequences = []
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("U", "T")
        # Take last inp_len nucleotides (as the training code does)
        seq = seq[-inp_len:]
        if len(seq) == 0:
            print(f"Warning: {header} has empty sequence, skipping", file=sys.stderr)
            continue
        sequences.append((header, seq))

    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sequences)} sequences, task={args.task}...", file=sys.stderr)

    # Build dataset
    headers = [h for h, _ in sequences]
    seqs = [s for _, s in sequences]
    dummy_labels = [0.0] * len(seqs)
    dataset = FastaBatchedDataset(dummy_labels, seqs, mask_prob=0.0)
    batches = dataset.get_batch_indices(toks_per_batch=BATCH_TOKS, extra_toks_per_seq=2)
    dataloader = torch.utils.data.DataLoader(
        dataset,
        collate_fn=alphabet.get_batch_converter(),
        batch_sampler=batches,
        shuffle=False,
    )

    # Predict — use custom checkpoint if provided, else bundled fold ensemble
    all_fold_preds = []
    if args.checkpoint:
        checkpoint_list = [(0, args.checkpoint)]
        print(f"  Using custom checkpoint: {args.checkpoint}", file=sys.stderr)
    else:
        checkpoint_list = [
            (fold_idx, find_checkpoint(args.model_dir, args.task, args.cell_line, fold_idx))
            for fold_idx in fold_indices
        ]

    for fold_idx, ckpt_path in checkpoint_list:
        if not args.checkpoint:
            print(f"  Loading fold {fold_idx}: {os.path.basename(ckpt_path)}", file=sys.stderr)

        model = CNNLinear(
            esm2_cls, alphabet, nodes=40, dropout3=dropout3, inp_len=inp_len
        ).to(device)
        state = torch.load(ckpt_path, map_location=device, weights_only=False)
        # Remove 'module.' prefix from DDP-trained state dicts
        state = {k.replace("module.", ""): v for k, v in state.items()}
        model.load_state_dict(state, strict=False)
        model.eval()

        fold_preds = []
        with torch.no_grad():
            for batch in dataloader:
                # CustomBatchConverter returns 6 items
                toks = batch[3].to(device)
                out = model(toks)
                fold_preds.extend(out.squeeze(-1).cpu().numpy().tolist())

        all_fold_preds.append(fold_preds)

    # Average across folds
    preds = np.mean(all_fold_preds, axis=0)

    # Write output
    os.makedirs(args.output, exist_ok=True)
    results_file = os.path.join(args.output, "predictions.tsv")
    task_label = {
        "mrl": "mean_ribosome_loading",
        "te": "translation_efficiency_log",
        "el": "expression_level_log",
    }
    with open(results_file, "w") as f:
        f.write(f"header\tsequence\t{task_label[args.task]}\n")
        for header, seq, pred in zip(headers, seqs, preds, strict=True):
            f.write(f"{header}\t{seq}\t{pred:.6f}\n")

    print(f"Done. {len(preds)} predictions written to {results_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
