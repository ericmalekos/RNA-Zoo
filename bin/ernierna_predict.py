#!/usr/bin/env python3
"""
CLI wrapper for ERNIE-RNA embedding extraction from RNA sequences.
Takes a FASTA of RNA sequences, outputs per-sequence and optionally per-token embeddings.
"""

import argparse
import os
import sys

# Patch torch.load for PyTorch >= 2.0 compatibility
import torch as _torch

__orig_load = _torch.load


def _patched_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return __orig_load(*args, **kwargs)


_torch.load = _patched_load

import numpy as np  # noqa: E402
import torch  # noqa: E402

# Register fairseq custom tasks/models/criterions
from src.ernie_rna.criterions.ernie_rna import *  # noqa: E402, F401, F403
from src.ernie_rna.models.ernie_rna import *  # noqa: E402, F401, F403
from src.ernie_rna.tasks.ernie_rna import *  # noqa: E402, F401, F403
from src.utils import (  # noqa: E402
    ErnieRNAOnestage,
    load_pretrained_ernierna,
    prepare_input_for_ernierna,
)

TOKEN_MAP = {
    "A": 5, "a": 5,
    "C": 7, "c": 7,
    "G": 4, "g": 4,
    "U": 6, "u": 6,
    "T": 6, "t": 6,
}


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


def seq_to_index(seq):
    """Convert RNA sequence to token indices with CLS/EOS."""
    length = len(seq)
    idx = np.ones(length + 2)
    idx[0] = 0  # CLS
    for j, c in enumerate(seq):
        idx[j + 1] = TOKEN_MAP.get(c, 3)  # UNK=3
    idx[length + 1] = 2  # EOS
    return idx, length


def main():
    parser = argparse.ArgumentParser(
        description="Extract ERNIE-RNA embeddings from RNA sequences"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="FASTA file of RNA sequences"
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output directory for embedding files"
    )
    parser.add_argument(
        "--per-token",
        action="store_true",
        help="Save per-token embeddings (L x 768 .npy per sequence)",
    )
    parser.add_argument(
        "--checkpoint",
        default="/opt/ernie-rna/checkpoint/ERNIE-RNA_checkpoint/ERNIE-RNA_pretrain.pt",
        help="Path to pretrained checkpoint",
    )
    parser.add_argument(
        "--dict-dir",
        default="/opt/ernie-rna/src/dict/",
        help="Path to fairseq dictionary directory",
    )
    parser.add_argument(
        "--max-len",
        type=int,
        default=1022,
        help="Maximum sequence length (default: 1022)",
    )
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}", file=sys.stderr)

    print("Loading ERNIE-RNA model...", file=sys.stderr)
    arg_overrides = {"data": args.dict_dir}
    model_pretrained = load_pretrained_ernierna(args.checkpoint, arg_overrides)
    model = ErnieRNAOnestage(model_pretrained.encoder).to(device)
    model.eval()

    os.makedirs(args.output, exist_ok=True)

    # Load sequences
    sequences = []
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("T", "U")
        if len(seq) > args.max_len:
            print(
                f"Warning: {header} ({len(seq)} nt) exceeds {args.max_len} nt, truncating",
                file=sys.stderr,
            )
            seq = seq[: args.max_len]
        if len(seq) == 0:
            print(f"Warning: {header} empty, skipping", file=sys.stderr)
            continue
        sequences.append((header, seq))

    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    all_seq_embeddings = []
    all_labels = []

    for idx, (header, seq) in enumerate(sequences):
        index, seq_len = seq_to_index(seq)
        one_d, two_d = prepare_input_for_ernierna(index, seq_len)
        one_d = one_d.to(device)
        two_d = two_d.to(device)

        with torch.no_grad():
            # Get last layer embeddings: shape [1, 1, L+2, 768]
            output = model(one_d, two_d, layer_idx=1)

        # CLS token embedding from last layer
        cls_emb = output[0, 0, 0, :].cpu().numpy()  # (768,)
        all_seq_embeddings.append(cls_emb)
        all_labels.append(header)

        if args.per_token:
            # Token embeddings excluding CLS and EOS
            tok_emb = output[0, 0, 1 : seq_len + 1, :].cpu().numpy()  # (L, 768)
            safe_name = header.replace("/", "_").replace(" ", "_")
            np.save(os.path.join(args.output, f"{safe_name}_tokens.npy"), tok_emb)

        if (idx + 1) % 10 == 0 or idx == len(sequences) - 1:
            print(f"  [{idx + 1}/{len(sequences)}] done", file=sys.stderr)

    seq_embeddings = np.stack(all_seq_embeddings)  # (N, 768)
    np.save(os.path.join(args.output, "sequence_embeddings.npy"), seq_embeddings)

    with open(os.path.join(args.output, "labels.txt"), "w") as f:
        for label in all_labels:
            f.write(label + "\n")

    print(
        f"Done. Saved {len(all_labels)} sequence embeddings "
        f"(shape: {seq_embeddings.shape}) to {args.output}/",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
