#!/usr/bin/env python3
"""
CLI wrapper for Orthrus mature-mRNA embedding extraction.
Takes a FASTA of mRNA sequences, outputs per-sequence (and optionally
per-token) embeddings using the v1 4-track Mamba encoder.
"""

import argparse
import os
import sys

import numpy as np
import torch
from orthrus.eval_utils import load_model
from orthrus.gk_utils import seq_to_oh

WEIGHTS_ROOT = "/opt/orthrus_weights"
DEFAULT_VARIANT = "v1_4_track"

VARIANTS = {
    "v1_4_track": {
        "run_dir": "orthrus_v1_4_track",
        "checkpoint": "epoch=6-step=20000.ckpt",
    },
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


def encode_sequence(seq):
    """U->T conversion + one-hot encode to (4, L) float32 tensor."""
    seq_dna = seq.upper().replace("U", "T")
    oh = seq_to_oh(seq_dna)  # (L, 4) int
    return torch.tensor(oh.T, dtype=torch.float32)  # (4, L)


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
        help=f"Model variant (default: {DEFAULT_VARIANT})",
    )
    parser.add_argument(
        "--per-token", action="store_true",
        help="Also save per-token embeddings (L x H .npy per sequence)",
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
    run_path = os.path.join(WEIGHTS_ROOT, variant_cfg["run_dir"])
    print(
        f"Loading Orthrus {args.variant} from {run_path}/{variant_cfg['checkpoint']}",
        file=sys.stderr,
    )
    model = load_model(run_path, checkpoint_name=variant_cfg["checkpoint"])
    model = model.to(device).eval()

    os.makedirs(args.output, exist_ok=True)

    sequences = []
    short_count = 0
    for header, seq in parse_fasta(args.input):
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
        oh = encode_sequence(seq).unsqueeze(0).to(device)  # (1, 4, L)
        lengths = torch.tensor([oh.shape[2]], device=device)

        with torch.no_grad():
            seq_emb = model.representation(oh, lengths).squeeze(0).cpu().numpy()  # (H,)

        all_seq_embeddings.append(seq_emb)
        all_labels.append(header)

        if args.per_token:
            with torch.no_grad():
                # forward returns (B, L, H) by default (channel_last=False
                # transposes from (B, C, L) input internally)
                tokens = model.forward(oh).squeeze(0).cpu().numpy()  # (L, H)
            safe_name = header.replace("/", "_").replace(" ", "_")
            np.save(os.path.join(args.output, f"{safe_name}_tokens.npy"), tokens)

    seq_embeddings = np.stack(all_seq_embeddings)  # (N, H)
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
