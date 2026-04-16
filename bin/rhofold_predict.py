#!/usr/bin/env python3
"""
CLI wrapper for RhoFold+ RNA 3D structure prediction.
Takes a FASTA of RNA sequences, predicts 3D structures in PDB format.
Runs in single-sequence mode (no MSA databases needed).
"""

import argparse
import os
import subprocess
import sys
import tempfile


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
        description="Predict RNA 3D structure with RhoFold+ (single-sequence mode)"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="FASTA file of RNA sequences"
    )
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--ckpt",
        default="/opt/rhofold/pretrained/rhofold_pretrained_params.pt",
        help="Path to RhoFold checkpoint",
    )
    parser.add_argument(
        "--relax-steps",
        type=int,
        default=0,
        help="Amber relaxation steps (default: 0 = skip relaxation)",
    )
    args = parser.parse_args()

    device = "cuda:0" if os.path.exists("/dev/nvidia0") else "cpu"
    print(f"Using device: {device}", file=sys.stderr)

    os.makedirs(args.output, exist_ok=True)

    sequences = list(parse_fasta(args.input))
    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    for idx, (header, seq) in enumerate(sequences):
        seq = seq.upper().replace("T", "U")
        safe_name = header.split()[0].replace("/", "_").replace(":", "_")
        seq_outdir = os.path.join(args.output, safe_name)
        os.makedirs(seq_outdir, exist_ok=True)

        # Write single-sequence FASTA
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".fa", delete=False, dir=args.output
        ) as tmp:
            tmp.write(f">{header}\n{seq}\n")
            tmp_path = tmp.name

        print(
            f"  [{idx + 1}/{len(sequences)}] {header} ({len(seq)} nt)",
            file=sys.stderr,
        )

        cmd = [
            sys.executable,
            "/opt/rhofold/inference.py",
            "--input_fas", tmp_path,
            "--single_seq_pred", "True",
            "--output_dir", seq_outdir,
            "--ckpt", args.ckpt,
            "--relax_steps", str(args.relax_steps),
            "--device", device,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  WARNING: RhoFold failed for {header}", file=sys.stderr)
            print(result.stderr[-500:] if result.stderr else "", file=sys.stderr)
        else:
            # Check output exists
            pdb_path = os.path.join(seq_outdir, "unrelaxed_model.pdb")
            if os.path.exists(pdb_path):
                print(f"  -> {pdb_path}", file=sys.stderr)

        os.unlink(tmp_path)

    print(f"Done. Results written to {args.output}/", file=sys.stderr)


if __name__ == "__main__":
    main()
