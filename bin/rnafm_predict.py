#!/usr/bin/env python3
"""
CLI wrapper for RNA-FM embedding extraction.
Takes a FASTA of RNA sequences, outputs per-sequence and per-token embeddings.
"""

import argparse
import os
import sys

import fm
import numpy as np
import torch


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


def main():
    parser = argparse.ArgumentParser(
        description="Extract RNA-FM embeddings from RNA sequences"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="FASTA file of RNA sequences (A/C/G/U)"
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output directory for embedding files"
    )
    parser.add_argument(
        "--per-token",
        action="store_true",
        help="Save per-token embeddings (L x 640 .npy per sequence) in addition to per-sequence",
    )
    parser.add_argument(
        "--max-len",
        type=int,
        default=1024,
        help="Maximum sequence length (default: 1024, the RNA-FM positional embedding limit)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Batch size for inference (default: 8)",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)

    print("Loading RNA-FM model...", file=sys.stderr)
    weights_path = "/opt/rnafm_weights/RNA-FM_pretrained.pth"
    if os.path.exists(weights_path):
        model, alphabet = fm.pretrained.rna_fm_t12(weights_path)
    else:
        model, alphabet = fm.pretrained.rna_fm_t12()
    batch_converter = alphabet.get_batch_converter()
    model.eval()
    model.to(device)

    os.makedirs(args.output, exist_ok=True)

    # Load and validate sequences
    sequences = []
    skipped = 0
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("T", "U")
        if len(seq) > args.max_len:
            print(
                f"Warning: {header} ({len(seq)} nt) exceeds {args.max_len} nt limit, truncating",
                file=sys.stderr,
            )
            seq = seq[: args.max_len]
        if len(seq) == 0:
            print(f"Warning: {header} has empty sequence, skipping", file=sys.stderr)
            skipped += 1
            continue
        sequences.append((header, seq))

    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    # Process in batches
    all_seq_embeddings = []
    all_labels = []

    for i in range(0, len(sequences), args.batch_size):
        batch_data = sequences[i : i + args.batch_size]
        batch_labels, batch_strs, batch_tokens = batch_converter(batch_data)
        batch_tokens = batch_tokens.to(device)

        with torch.no_grad():
            results = model(batch_tokens, repr_layers=[12])

        token_embeddings = results["representations"][12]  # (B, L+2, 640)

        for j, label in enumerate(batch_labels):
            seq_len = len(batch_strs[j])
            # Extract embeddings for actual sequence positions (skip BOS/EOS tokens)
            emb = token_embeddings[j, 1 : seq_len + 1, :].cpu().numpy()  # (L, 640)

            # Per-sequence embedding: mean pool over positions
            seq_emb = emb.mean(axis=0)  # (640,)
            all_seq_embeddings.append(seq_emb)
            all_labels.append(label)

            if args.per_token:
                safe_name = label.replace("/", "_").replace(" ", "_")
                np.save(os.path.join(args.output, f"{safe_name}_tokens.npy"), emb)

        print(
            f"  Batch {i // args.batch_size + 1}/"
            f"{(len(sequences) + args.batch_size - 1) // args.batch_size} done",
            file=sys.stderr,
        )

    # Save per-sequence embeddings as a single file
    seq_embeddings = np.stack(all_seq_embeddings)  # (N, 640)
    np.save(os.path.join(args.output, "sequence_embeddings.npy"), seq_embeddings)

    # Save labels
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
