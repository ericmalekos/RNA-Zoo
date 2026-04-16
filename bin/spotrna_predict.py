#!/usr/bin/env python3
"""
CLI wrapper for SPOT-RNA secondary structure prediction (including pseudoknots).
Takes a FASTA of RNA sequences, outputs bpseq, ct, and dot-bracket structures.
"""

import argparse
import os
import shutil
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


def bpseq_to_dotbracket(bpseq_path):
    """Convert bpseq file to dot-bracket notation with pseudoknot support."""
    pairs = []
    length = 0
    with open(bpseq_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 3:
                idx = int(parts[0]) - 1  # 0-indexed
                partner = int(parts[2]) - 1  # 0-indexed, -1 means unpaired
                length = max(length, idx + 1)
                if partner >= 0 and idx < partner:
                    pairs.append((idx, partner))

    structure = ["."] * length
    pk_chars = [("(", ")"), ("[", "]"), ("{", "}")]

    sorted_pairs = sorted(pairs, key=lambda p: p[0])

    levels = [[] for _ in pk_chars]
    for i, j in sorted_pairs:
        for level_idx, level_pairs in enumerate(levels):
            conflict = False
            for pi, pj in level_pairs:
                if (i < pi < j < pj) or (pi < i < pj < j):
                    conflict = True
                    break
            if not conflict:
                level_pairs.append((i, j))
                open_char, close_char = pk_chars[level_idx]
                structure[i] = open_char
                structure[j] = close_char
                break

    return "".join(structure)


def main():
    parser = argparse.ArgumentParser(
        description="Predict RNA secondary structure (incl. pseudoknots) with SPOT-RNA"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="FASTA file of RNA sequences"
    )
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--plot", action="store_true",
        help="Generate contact map heatmap PNGs for each sequence",
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Collect sequences
    sequences = list(parse_fasta(args.input))
    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    structures_file = os.path.join(args.output, "structures.txt")

    with open(structures_file, "w") as sf:
        for idx, (header, seq) in enumerate(sequences):
            seq = seq.upper().replace("T", "U")
            # Sanitize header for filename safety
            safe_name = header.split()[0].replace("/", "_").replace(":", "_")

            # Write single-sequence FASTA to temp file
            # (SPOT-RNA overwrites input in-place — use a copy)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".fasta", delete=False
            ) as tmp:
                tmp.write(f">{safe_name}\n{seq}\n")
                tmp_path = tmp.name

            # Create temp output dir for this sequence
            tmp_outdir = tempfile.mkdtemp()

            cmd = [
                sys.executable,
                "/opt/SPOT-RNA/SPOT-RNA.py",
                "--inputs", tmp_path,
                "--outputs", tmp_outdir + "/",
                "--gpu", "-1",
                "--cpu", "4",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            bpseq_path = os.path.join(tmp_outdir, f"{safe_name}.bpseq")
            ct_path = os.path.join(tmp_outdir, f"{safe_name}.ct")
            prob_path = os.path.join(tmp_outdir, f"{safe_name}.prob")

            if result.returncode != 0 or not os.path.exists(bpseq_path):
                print(
                    f"  WARNING: SPOT-RNA failed for {header}", file=sys.stderr
                )
                if result.stderr:
                    print(result.stderr[-300:], file=sys.stderr)
            else:
                # Convert bpseq to dot-bracket
                db = bpseq_to_dotbracket(bpseq_path)
                sf.write(f">{header}\n{seq}\n{db}\n")

                # Copy output files to final location
                for src in [bpseq_path, ct_path, prob_path]:
                    if os.path.exists(src):
                        shutil.copy2(src, args.output)

                # Plot contact map from probability matrix
                if args.plot and os.path.exists(prob_path):
                    import numpy as np
                    from rnazoo_plots import plot_contact_map

                    prob_mat = np.loadtxt(prob_path)
                    plot_contact_map(
                        prob_mat, seq, header,
                        os.path.join(args.output, f"{safe_name}_contact.png"),
                        title_prefix="SPOT-RNA: ",
                    )

                print(
                    f"  [{idx + 1}/{len(sequences)}] {header} ({len(seq)} nt)",
                    file=sys.stderr,
                )

            # Clean up
            os.unlink(tmp_path)
            shutil.rmtree(tmp_outdir, ignore_errors=True)

    print(f"Done. Results written to {args.output}/", file=sys.stderr)


if __name__ == "__main__":
    main()
