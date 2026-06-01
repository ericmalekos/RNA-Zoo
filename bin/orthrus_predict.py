#!/usr/bin/env python3
"""
CLI wrapper for Orthrus mature-mRNA embedding extraction.
Takes a FASTA of mRNA sequences, outputs per-sequence (and optionally
per-token) embeddings using one of the three bundled 4-track variants.

Variants and their embedding dimensions:
  4track       (antichronology/orthrus-4-track)      512-d  [default]
  large-4track (quietflamingo/orthrus-large-4-track) 512-d
  base-4track  (quietflamingo/orthrus-base-4-track)  256-d

Uses the standardized AutoModel API (trust_remote_code=True).
"""

import argparse
import os
import sys

import numpy as np
import torch
from transformers import AutoModel

WEIGHTS_ROOT = "/opt/orthrus_weights"
DEFAULT_VARIANT = "4track"

VARIANTS = {
    "4track": {
        "local_dir": "orthrus-4-track",
        "embed_dim": 512,
    },
    "large-4track": {
        "local_dir": "orthrus-large-4-track",
        "embed_dim": 512,
    },
    "base-4track": {
        "local_dir": "orthrus-base-4-track",
        "embed_dim": 256,
    },
    # Legacy alias kept for backward compatibility with --orthrus_variant v1_4_track.
    "v1_4_track": {
        "local_dir": "orthrus-4-track",
        "embed_dim": 512,
    },
}


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
        description="Extract Orthrus embeddings from mature mRNA sequences"
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="FASTA of complete mature mRNA sequences (A/C/G/U or A/C/G/T)",
    )
    parser.add_argument(
        "-o", "--output", required=True,
        help="Output directory for embedding files",
    )
    parser.add_argument(
        "--variant", default=DEFAULT_VARIANT, choices=sorted(VARIANTS.keys()),
        help=f"Model variant (default: {DEFAULT_VARIANT}). "
             "4track/large-4track → 512-d; base-4track → 256-d",
    )
    parser.add_argument(
        "--per-token", action="store_true",
        help="Also save per-token embeddings (L x D .npy per sequence)",
    )
    parser.add_argument(
        "--min-len", type=int, default=200,
        help="Warn (do not fail) when a sequence is shorter than this; "
             "Orthrus is trained on full mature transcripts and partial "
             "sequences fall out-of-distribution (default: 200)",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)
    if device.type != "cuda":
        print(
            "Warning: Orthrus uses Mamba's CUDA selective-scan kernel; "
            "running on CPU is not supported by the bundled mamba-ssm wheel.",
            file=sys.stderr,
        )

    variant_cfg = VARIANTS[args.variant]
    weights_path = os.path.join(WEIGHTS_ROOT, variant_cfg["local_dir"])
    print(f"Loading Orthrus variant '{args.variant}' from {weights_path}", file=sys.stderr)
    model = AutoModel.from_pretrained(
        weights_path,
        trust_remote_code=True,
    ).to(device).eval()

    os.makedirs(args.output, exist_ok=True)

    sequences = []
    short_count = 0
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("U", "T")
        if not seq:
            print(f"Warning: {header} is empty, skipping", file=sys.stderr)
            continue
        if len(seq) < args.min_len:
            short_count += 1
            print(
                f"Warning: {header} is {len(seq)} nt (< {args.min_len}); "
                "Orthrus expects complete mature transcripts — embedding may be OOD",
                file=sys.stderr,
            )
        sequences.append((header, seq))

    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    all_seq_embeddings = []
    all_labels = []

    for header, seq in sequences:
        # seq_to_oh returns (L, 4); unsqueeze → (1, L, 4) for channel_last=True API
        oh = model.seq_to_oh(seq).unsqueeze(0).to(device)
        lengths = torch.tensor([oh.shape[1]], device=device)

        with torch.no_grad():
            seq_emb = model.representation(oh, lengths, channel_last=True)  # (1, D)
        all_seq_embeddings.append(seq_emb.squeeze(0).cpu().numpy())
        all_labels.append(header)

        if args.per_token:
            with torch.no_grad():
                tokens = model.representation_unpooled(oh, channel_last=True)  # (1, L, D)
            safe_name = header.replace("/", "_").replace(" ", "_")
            np.save(
                os.path.join(args.output, f"{safe_name}_tokens.npy"),
                tokens.squeeze(0).cpu().numpy(),
            )

    seq_embeddings = np.stack(all_seq_embeddings)  # (N, D)
    np.save(os.path.join(args.output, "sequence_embeddings.npy"), seq_embeddings)

    with open(os.path.join(args.output, "labels.txt"), "w") as f:
        for label in all_labels:
            f.write(label + "\n")

    print(
        f"Done. Saved {len(all_labels)} sequence embeddings "
        f"(shape: {seq_embeddings.shape}) to {args.output}/",
        file=sys.stderr,
    )
    if short_count:
        print(
            f"Note: {short_count} sequences were shorter than {args.min_len} nt "
            "and may produce out-of-distribution embeddings.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
