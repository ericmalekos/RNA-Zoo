#!/usr/bin/env python3
"""
Adapter: TSV/CSV with (name, sequence, label) columns → FASTA + numeric labels.txt.

Used by foundation-model linear-probe fine-tune wrappers as Step 1 of
the 3-step pipeline:
  TSV/CSV → [this script] → FASTA + labels.txt → [predict] → embeddings → [head trainer]

Required CSV/TSV format:
  - Header row required.
  - Columns `name` and `sequence` are required (order doesn't matter).
  - The label column is configurable via --label-col (default: 'label').
  - Labels must be numeric (parsed as float).

Output paths:
  <out_basename>.fa          — FASTA, one record per row
  <out_basename>_labels.txt  — one float per line, same order
"""

import argparse
import csv
import os
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", required=True, help="TSV or CSV path")
    parser.add_argument(
        "-o", "--out-basename", required=True,
        help="Output basename (writes <basename>.fa and <basename>_labels.txt)",
    )
    parser.add_argument(
        "--label-col", default="label",
        help="Name of the label column in the input file (default: 'label')",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(args.input)[1].lower()
    delim = "," if ext == ".csv" else "\t"

    fasta_path = f"{args.out_basename}.fa"
    labels_path = f"{args.out_basename}_labels.txt"

    n_written = 0
    with open(args.input, newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        if reader.fieldnames is None:
            print(f"ERROR: no header row in {args.input}", file=sys.stderr)
            sys.exit(1)
        cols_lower = [c.strip().lower() for c in reader.fieldnames]
        for required in ("name", "sequence"):
            if required not in cols_lower:
                print(
                    f"ERROR: required column '{required}' not in header "
                    f"{reader.fieldnames}",
                    file=sys.stderr,
                )
                sys.exit(1)
        if args.label_col not in reader.fieldnames:
            print(
                f"ERROR: label column '{args.label_col}' not in header "
                f"{reader.fieldnames}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Resolve original-cased column names for case-insensitive matching
        name_key = next(c for c in reader.fieldnames if c.strip().lower() == "name")
        seq_key = next(c for c in reader.fieldnames if c.strip().lower() == "sequence")

        with open(fasta_path, "w") as fa, open(labels_path, "w") as labf:
            for i, row in enumerate(reader):
                name = (row[name_key] or "").strip()
                seq = (row[seq_key] or "").strip()
                lab_str = (row[args.label_col] or "").strip()
                if not name or not seq:
                    print(
                        f"ERROR: row {i + 2}: empty name or sequence",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                try:
                    lab = float(lab_str)
                except ValueError:
                    print(
                        f"ERROR: row {i + 2}: label '{lab_str}' is not numeric",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                fa.write(f">{name}\n{seq}\n")
                labf.write(f"{lab}\n")
                n_written += 1

    if n_written == 0:
        print(f"ERROR: no data rows in {args.input}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Wrote {n_written} records to {fasta_path} + {labels_path}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
