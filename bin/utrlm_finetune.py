#!/usr/bin/env python3
"""
UTR-LM fine-tuning wrapper.
Fine-tunes the pretrained UTR-LM backbone and a new head on user-provided 5'UTR
expression data (MRL, TE, or EL) for a new dataset or condition, starting from the
backbone and using the optimizer and loss of upstream's fine-tuning scripts.
docs/models/UTRLM.md lists where the training still differs from those scripts.

Input: CSV/TSV with columns: name, utr (5'UTR sequence), <label_column> (numeric target)
Output: fine-tuned model checkpoint + predictions on held-out test set
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from esm.data import Alphabet, FastaBatchedDataset
from esm.model.esm2_secondarystructure import ESM2 as ESM2_SISS
from esm.model.esm2_supervised import ESM2 as ESM2_SI
from torch.utils.data import DataLoader, Dataset

LAYERS = 6
HEADS = 16
EMBED_DIM = 128

# Pretrained backbone that upstream's fine-tuning starts from, per task: the `--modelfile` of the
# commands in the upstream README, "UTR-LM downstream fine-tuning process" (section 1 runs
# MJ3_Finetune_extract_append_predictor_Sample_10fold-lr-huber-DDP.py for MRL, section 2 runs
# MJ4_Finetune_extract_append_predictor_CellLine_10fold-lr-huber-DDP.py for TE and EL; MJ4's
# own `--modelfile` default is the same TE/EL file). The README gives the TE/EL file directly
# under Model/; the repository keeps it in Model/Pretrained/ (Model/ holds only a 4 kB macOS
# metadata file of that name).
PRETRAINED_BACKBONES = {
    "mrl": "ESM2SISS_FS4.1_fiveSpeciesCao_6layers_16heads_128embedsize_4096batchToks_lr1e-05_"
    "supervisedweight1.0_structureweight1.0_MLMLossMin_epoch93.pkl",
    "te": "ESM2SI_3.1_fiveSpeciesCao_6layers_16heads_128embedsize_4096batchToks_MLMLossMin.pkl",
    "el": "ESM2SI_3.1_fiveSpeciesCao_6layers_16heads_128embedsize_4096batchToks_MLMLossMin.pkl",
}
# Output layers of the pretraining objectives (minimum free energy, secondary structure). The
# backbone variants differ only in which of them they carry, and the downstream predictor never
# uses them, so a checkpoint may lack them or carry ones the task's backbone does not have.
PRETRAINING_HEADS = ("supervised_linear.", "structure_linear.")
HEAD_LAYERS = ("fc.", "output.")


class CNNLinear(nn.Module):
    """Downstream predictor: ESM2 backbone + FC head."""

    def __init__(self, esm2_cls, alphabet, nodes=40, dropout3=0.5, inp_len=50):
        super().__init__()
        self.inp_len = inp_len
        self.esm2 = esm2_cls(
            num_layers=LAYERS, embed_dim=EMBED_DIM,
            attention_heads=HEADS, alphabet=alphabet,
        )
        self.dropout3 = nn.Dropout(dropout3)
        self.relu = nn.ReLU()
        self.flatten = nn.Flatten()
        self.fc = nn.Linear(in_features=EMBED_DIM, out_features=nodes)
        self.output = nn.Linear(in_features=nodes, out_features=1)

    def forward(self, tokens):
        x = self.esm2(
            tokens, [LAYERS], need_head_weights=False,
            return_contacts=False, return_representation=True,
        )
        x = x["representations"][LAYERS][:, 0]  # CLS token
        x_o = x.unsqueeze(2)
        x = self.flatten(x_o)
        o = self.output(self.dropout3(self.relu(self.fc(x))))
        return o


class UTRDataset(Dataset):
    """Simple dataset: sequences + labels."""

    def __init__(self, sequences, labels, alphabet, max_len):
        self.sequences = [s[-max_len:] for s in sequences]
        self.labels = labels
        self.alphabet = alphabet

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx]

    def collate(self, batch):
        seqs, labels = zip(*batch, strict=True)
        # UTR-LM's batch converter takes each sequence as the 4 fields that its
        # FastaBatchedDataset yields (label, sequence, masked sequence, masked positions);
        # mask_prob=0 leaves the sequences unmasked, as in upstream fine-tuning.
        records = FastaBatchedDataset(labels, seqs, mask_prob=0.0)
        bc = self.alphabet.get_batch_converter()
        result = bc([records[i] for i in range(len(records))])  # returns 6 items
        tokens = result[3]  # index 3 = tokens
        return tokens, torch.tensor(labels, dtype=torch.float32)


def load_start_weights(model, path, task):
    """Load the starting weights from path into model; exit unless the whole backbone loads.

    Takes a backbone-only checkpoint (upstream's Model/Pretrained/*.pkl, whose tensor names are
    the backbone's own) or a whole predictor (a best_model.pt from this script, or upstream's
    Model/Downstream/*.pt), whose backbone sits under 'esm2.' beside the head. Every backbone
    tensor must load, apart from the PRETRAINING_HEADS layers. A load with strict=False and no
    check (as upstream does) leaves the backbone at random weights whenever the names differ.
    """
    state = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(state, dict):
        sys.exit(f"Error: {path} holds a {type(state).__name__}, not a state dict of tensors")
    state = {k.removeprefix("module."): v for k, v in state.items()}  # saved from DDP
    if any(k.startswith("esm2.") for k in state):
        backbone = {k.removeprefix("esm2."): v for k, v in state.items() if k.startswith("esm2.")}
        head = {k: v for k, v in state.items() if k.startswith(HEAD_LAYERS)}
        ignored = sorted(
            {k.split(".")[0] for k in state if not k.startswith(("esm2.", *HEAD_LAYERS))}
        )
    else:
        backbone, head, ignored = state, {}, []

    own = model.esm2.state_dict()
    own_head = {k: v for k, v in model.state_dict().items() if k.startswith(HEAD_LAYERS)}
    fits = {k: v for k, v in backbone.items() if k in own and own[k].shape == v.shape}
    surplus = sorted(k for k in backbone if k not in fits)  # no counterpart, or other shape
    lacking = sorted(k for k in own if k not in fits)

    def body(keys):  # leaves out the pretraining heads
        return [k for k in keys if not k.startswith(PRETRAINING_HEADS)]

    missing = body(k for k in own if k not in backbone)
    unknown = body(k for k in backbone if k not in own)
    reshaped = body(k for k in backbone if k in own and own[k].shape != backbone[k].shape)
    bad_head = sorted(
        k for k, v in head.items() if k not in own_head or own_head[k].shape != v.shape
    )
    if missing or unknown or reshaped or bad_head:
        sys.exit(
            f"Error: {path} does not fit the {task} model, so nothing was loaded: "
            f"{len(fits)} of the model's {len(own)} backbone tensors would load. Backbone "
            f"tensors missing from the file: {len(missing)} {missing[:3]}; in the file but not "
            f"in the model: {len(unknown)} {unknown[:3]}; of another shape: {len(reshaped)} "
            f"{reshaped[:3]}; head tensors that do not fit: {len(bad_head)} {bad_head[:3]} "
            f"(pretraining heads are not counted)."
        )
    model.esm2.load_state_dict(fits, strict=False)
    model.load_state_dict(head, strict=False)

    report = f"backbone {len(fits)} of {len(own)} tensors loaded"
    if lacking:
        report += f" ({len(lacking)} pretraining-head tensors left at random values: {lacking})"
    if surplus:
        report += f", {len(surplus)} pretraining-head tensors of the file skipped: {surplus}"
    if head:
        report += f"; head {len(head)} of {len(own_head)} tensors loaded"
    else:
        report += "; new head, randomly initialized"
    if ignored:
        report += f"; layers ignored (not in this model): {', '.join(ignored)}"
    print(f"Starting weights from {path}: {report}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune UTR-LM on user expression data"
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="CSV/TSV with columns: name, utr, <label_column>",
    )
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--label", required=True,
        help="Column name containing target values (MRL/TE/EL)",
    )
    parser.add_argument(
        "--task", default="mrl", choices=["mrl", "te", "el"],
        help="Task type (determines the backbone, its default pretrained weights and the input "
        "length). Default: mrl",
    )
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs")
    parser.add_argument("--patience", type=int, default=20, help="Early stopping patience")
    parser.add_argument(
        "--lr", type=float, default=0.01, help="SGD learning rate (default: 0.01, as upstream)"
    )
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--val-frac", type=float, default=0.2, help="Validation fraction")
    parser.add_argument(
        "--pretrained",
        default=None,
        help="Starting weights: a backbone-only pretraining checkpoint or a whole-predictor "
        "checkpoint (a best_model.pt, or a bundled Downstream model). Default: the pretrained "
        "backbone that upstream's fine-tuning uses for the task, from <model-dir>/Pretrained. "
        "'none': random weights.",
    )
    parser.add_argument(
        "--model-dir", default="/opt/utrlm/Model",
        help="Path to Model directory",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)

    os.makedirs(args.output, exist_ok=True)

    # Determine task params
    if args.task == "mrl":
        esm2_cls = ESM2_SISS
        inp_len = 50
        dropout3 = 0.5
    else:
        esm2_cls = ESM2_SI
        inp_len = 100
        dropout3 = 0.2

    # Load data
    sep = "\t" if args.input.endswith(".tsv") else ","
    df = pd.read_csv(args.input, sep=sep)
    df = df.dropna(subset=[args.label])
    sequences = df["utr"].str.upper().str.replace("U", "T", regex=False).tolist()
    labels = df[args.label].astype(float).tolist()
    print(f"Loaded {len(sequences)} sequences", file=sys.stderr)

    # Train/val split
    n = len(sequences)
    n_val = max(1, int(n * args.val_frac))
    indices = np.random.RandomState(42).permutation(n)
    val_idx = indices[:n_val]
    train_idx = indices[n_val:]

    alphabet = Alphabet(standard_toks="AGCT", mask_prob=0.0)

    train_ds = UTRDataset(
        [sequences[i] for i in train_idx],
        [labels[i] for i in train_idx],
        alphabet, inp_len,
    )
    val_ds = UTRDataset(
        [sequences[i] for i in val_idx],
        [labels[i] for i in val_idx],
        alphabet, inp_len,
    )

    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True, collate_fn=train_ds.collate
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False, collate_fn=val_ds.collate
    )

    # Build model
    model = CNNLinear(esm2_cls, alphabet, nodes=40, dropout3=dropout3, inp_len=inp_len).to(device)

    # Starting weights: by default the task's pretrained backbone, as upstream fine-tunes
    if args.pretrained is not None and args.pretrained.lower() == "none":
        print("Starting weights: random initialization (--pretrained none)", file=sys.stderr)
    else:
        start = args.pretrained or os.path.join(
            args.model_dir, "Pretrained", PRETRAINED_BACKBONES[args.task]
        )
        if not os.path.isfile(start):
            sys.exit(f"Error: starting checkpoint not found: {start}")
        load_start_weights(model, start, args.task)

    # Upstream's fine-tuning optimizer for all three tasks (MJ3 and MJ4 scripts in
    # Scripts/UTRLM_downstream/): SGD with momentum 0.9 and weight decay 1e-4 over every
    # parameter. Neither script uses a learning-rate schedule (both import StepLR and never
    # create it). The Huber loss is upstream's too (its `--huber_loss`).
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=0.9, weight_decay=1e-4)
    loss_fn = nn.HuberLoss()

    best_val_loss = float("inf")
    patience_counter = 0
    best_path = os.path.join(args.output, "best_model.pt")

    for epoch in range(args.epochs):
        # Train
        model.train()
        train_loss = 0
        for tokens, targets in train_loader:
            tokens = tokens.to(device)
            targets = targets.to(device)
            preds = model(tokens).squeeze(-1)
            loss = loss_fn(preds, targets)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(targets)
        train_loss /= len(train_ds)

        # Validate
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for tokens, targets in val_loader:
                tokens = tokens.to(device)
                targets = targets.to(device)
                preds = model(tokens).squeeze(-1)
                val_loss += loss_fn(preds, targets).item() * len(targets)
        val_loss /= len(val_ds)

        if (epoch + 1) % 10 == 0:
            print(
                f"  Epoch {epoch + 1}/{args.epochs}  "
                f"train_loss={train_loss:.4f}  val_loss={val_loss:.4f}",
                file=sys.stderr,
            )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), best_path)
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"  Early stopping at epoch {epoch + 1}", file=sys.stderr)
                break

    # Reload best and predict on full dataset
    model.load_state_dict(torch.load(best_path, map_location=device, weights_only=True))
    model.eval()

    full_ds = UTRDataset(sequences, labels, alphabet, inp_len)
    full_loader = DataLoader(
        full_ds, batch_size=args.batch_size, shuffle=False, collate_fn=full_ds.collate
    )

    all_preds = []
    with torch.no_grad():
        for tokens, _ in full_loader:
            tokens = tokens.to(device)
            preds = model(tokens).squeeze(-1)
            all_preds.extend(preds.cpu().numpy().tolist())

    # Save predictions
    df["predicted"] = all_preds
    pred_path = os.path.join(args.output, "predictions.tsv")
    df.to_csv(pred_path, sep="\t", index=False)

    print(f"Done. Best model saved to {best_path}", file=sys.stderr)
    print(f"Predictions written to {pred_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
