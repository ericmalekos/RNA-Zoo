#!/usr/bin/env python3
"""
CLI wrapper for CaLM (Codon adaptation Language Model) embedding extraction.
Takes a FASTA of RNA / CDS sequences, outputs per-sequence (and optionally
per-codon) embeddings using the BSD-3-Clause oxpig/CaLM checkpoint.

CaLM is a codon-level RNA LM (12L / 768-dim, max 1024 codons). Input is
tokenized as in-frame 3-mers via the upstream CodonSequence class, which
handles T->U conversion. Sequences whose length is not a multiple of 3
yield a final partial codon that maps to <unk> — we trim to the largest
multiple of 3 and warn.
"""

import argparse
import os
import sys

import numpy as np
import torch
from calm import CaLM
from calm.sequence import CodonSequence

WEIGHTS_PATH = "/opt/calm_weights/calm_weights.pkl"
HIDDEN_DIM = 768
MAX_CODONS = 1024  # max_positions in upstream _ARGS


def parse_fasta(path):
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


def main():
    parser = argparse.ArgumentParser(
        description="Extract CaLM codon-level embeddings from RNA / CDS sequences"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="FASTA file of RNA/CDS sequences (A/C/G/U or A/C/G/T)"
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output directory for embedding files"
    )
    parser.add_argument(
        "--per-token",
        action="store_true",
        help="Save per-codon embeddings (L+2 x 768 .npy per sequence; includes <cls> and <eos>)",
    )
    parser.add_argument(
        "--max-codons",
        type=int,
        default=MAX_CODONS,
        help=f"Maximum codon count per sequence (default: {MAX_CODONS}). CaLM has "
             "max_positions=1024 codons.",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)

    print(f"Loading CaLM model from {WEIGHTS_PATH}...", file=sys.stderr)
    model = CaLM(weights_file=WEIGHTS_PATH)
    model.model.eval().to(device)

    os.makedirs(args.output, exist_ok=True)

    sequences = []
    skipped = 0
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("T", "U")
        if not seq:
            print(f"Warning: {header} has empty sequence, skipping", file=sys.stderr)
            skipped += 1
            continue
        if len(seq) % 3 != 0:
            trim = len(seq) - (len(seq) % 3)
            print(
                f"Warning: {header} ({len(seq)} nt) is not codon-aligned, "
                f"trimming to {trim} nt",
                file=sys.stderr,
            )
            seq = seq[:trim]
        n_codons = len(seq) // 3
        if n_codons > args.max_codons:
            print(
                f"Warning: {header} ({n_codons} codons) exceeds {args.max_codons}, "
                f"truncating",
                file=sys.stderr,
            )
            seq = seq[: args.max_codons * 3]
        sequences.append((header, seq))

    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    all_seq_embeddings = []
    all_labels = []

    for i, (header, seq) in enumerate(sequences):
        codon_seq = CodonSequence(seq)
        tokens = model.tokenize(codon_seq).to(device)

        with torch.no_grad():
            # repr_: (1, L+2, 768) — L+2 because <cls> and <eos> are added
            repr_ = model.model(tokens, repr_layers=[12])["representations"][12]

        # Mean-pool excluding <cls> at pos 0 and <eos> at last position,
        # matching the foundation-model convention used elsewhere in
        # RNAZoo (RNA-FM, RiNALMo, RNAErnie, PlantRNA-FM).
        seq_emb = repr_[:, 1:-1, :].mean(dim=1).squeeze(0).cpu().numpy()  # (768,)
        all_seq_embeddings.append(seq_emb)
        all_labels.append(header)

        if args.per_token:
            tok_emb = repr_.squeeze(0).cpu().numpy()  # (L+2, 768)
            safe_name = header.replace("/", "_").replace(" ", "_")
            np.save(os.path.join(args.output, f"{safe_name}_tokens.npy"), tok_emb)

        if (i + 1) % 10 == 0 or (i + 1) == len(sequences):
            print(f"  {i + 1}/{len(sequences)} done", file=sys.stderr)

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
    if skipped:
        print(f"Skipped {skipped} empty sequences.", file=sys.stderr)


if __name__ == "__main__":
    main()
