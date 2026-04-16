#!/usr/bin/env python3
"""
CLI wrapper for RiNALMo RNA embedding extraction.
Takes a FASTA of RNA sequences, outputs per-sequence and optionally per-token embeddings.
"""

import argparse
import os
import sys

import numpy as np
import torch
from rinalmo.pretrained import get_pretrained_model


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
        description="Extract RiNALMo embeddings from RNA sequences"
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
        help="Save per-token embeddings (L x D .npy per sequence) in addition to per-sequence",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Batch size for inference (default: 1; large model benefits from small batches)",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)

    print("Loading RiNALMo model...", file=sys.stderr)
    model, alphabet = get_pretrained_model(model_name="giga-v1")
    model = model.to(device)
    model.eval()

    os.makedirs(args.output, exist_ok=True)

    # Load and validate sequences
    sequences = []
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("T", "U")
        if len(seq) == 0:
            print(f"Warning: {header} has empty sequence, skipping", file=sys.stderr)
            continue
        sequences.append((header, seq))

    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    all_seq_embeddings = []
    all_labels = []

    for i in range(0, len(sequences), args.batch_size):
        batch_data = sequences[i : i + args.batch_size]
        headers = [h for h, _ in batch_data]
        seqs = [s for _, s in batch_data]

        tokens = torch.tensor(
            alphabet.batch_tokenize(seqs), dtype=torch.int64, device=device
        )

        with torch.no_grad():
            outputs = model(tokens)

        # representation shape: (B, L+2, embed_dim) where +2 = CLS + EOS
        representations = outputs["representation"].float().cpu().numpy()

        for j, (header, seq) in enumerate(zip(headers, seqs, strict=True)):
            seq_len = len(seq)
            # Tokens: [CLS, tok1, ..., tokN, EOS, PAD...]
            emb = representations[j, 1 : seq_len + 1, :]  # (L, embed_dim)

            seq_emb = emb.mean(axis=0)  # (embed_dim,)
            all_seq_embeddings.append(seq_emb)
            all_labels.append(header)

            if args.per_token:
                safe_name = header.replace("/", "_").replace(" ", "_")
                np.save(os.path.join(args.output, f"{safe_name}_tokens.npy"), emb)

        print(
            f"  Batch {i // args.batch_size + 1}/"
            f"{(len(sequences) + args.batch_size - 1) // args.batch_size} done",
            file=sys.stderr,
        )

    seq_embeddings = np.stack(all_seq_embeddings)  # (N, embed_dim)
    np.save(os.path.join(args.output, "sequence_embeddings.npy"), seq_embeddings)

    with open(os.path.join(args.output, "labels.txt"), "w") as f:
        for label in all_labels:
            f.write(label + "\n")

    embed_dim = seq_embeddings.shape[1]
    print(
        f"Done. Saved {len(all_labels)} sequence embeddings "
        f"(shape: {seq_embeddings.shape}, dim={embed_dim}) to {args.output}/",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
