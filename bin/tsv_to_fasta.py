#!/usr/bin/env python3
"""
Adapter: TSV/CSV with (name, sequence, label) columns → FASTA + numeric labels.txt.

Used by foundation-model linear-probe fine-tune wrappers as Step 1 of
the 3-step pipeline:
  TSV/CSV → [this script] → FASTA + labels.txt → [predict] → embeddings → [head trainer]

Required CSV/TSV format (default mode):
  - Header row required.
  - Columns `name` and `sequence` are required (order doesn't matter).
  - The label column is configurable via --label-col (default: 'label').
  - Labels may be numeric (regression) or string class names (classification);
    the head trainer (`finetune_head.py`) decides parsing based on --task.

`--no-fasta` mode (precomputed-embeddings short-circuit):
  - `sequence` column is no longer required (and is ignored if present).
  - Skips writing <out_basename>.fa.
  - Also writes <out_basename>_names.txt (one name per line, same order as labels)
    so the head trainer can label predictions without parsing a FASTA.

Output paths:
  <out_basename>.fa          — FASTA, one record per row (default mode only)
  <out_basename>_labels.txt  — one float per line, same order
  <out_basename>_names.txt   — one name per line, same order (--no-fasta only)
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
    parser.add_argument(
        "--no-fasta", action="store_true",
        help="Skip FASTA output; only write <basename>_labels.txt and "
             "<basename>_names.txt. The `sequence` column becomes optional.",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(args.input)[1].lower()
    delim = "," if ext == ".csv" else "\t"

    fasta_path = f"{args.out_basename}.fa"
    labels_path = f"{args.out_basename}_labels.txt"
    names_path = f"{args.out_basename}_names.txt"

    n_written = 0
    with open(args.input, newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        if reader.fieldnames is None:
            print(f"ERROR: no header row in {args.input}", file=sys.stderr)
            sys.exit(1)
        cols_lower = [c.strip().lower() for c in reader.fieldnames]
        required_cols = ("name",) if args.no_fasta else ("name", "sequence")
        for required in required_cols:
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
        seq_key = None
        if not args.no_fasta:
            seq_key = next(c for c in reader.fieldnames if c.strip().lower() == "sequence")

        fa = open(fasta_path, "w") if not args.no_fasta else None
        labf = open(labels_path, "w")
        namef = open(names_path, "w") if args.no_fasta else None
        try:
            for i, row in enumerate(reader):
                name = (row[name_key] or "").strip()
                lab_str = (row[args.label_col] or "").strip()
                if not name:
                    print(
                        f"ERROR: row {i + 2}: empty name",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                if not args.no_fasta:
                    seq = (row[seq_key] or "").strip()
                    if not seq:
                        print(
                            f"ERROR: row {i + 2}: empty sequence",
                            file=sys.stderr,
                        )
                        sys.exit(1)
                if not lab_str:
                    print(
                        f"ERROR: row {i + 2}: empty label",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                if fa is not None:
                    fa.write(f">{name}\n{seq}\n")
                # Pass labels through verbatim; finetune_head.py decides parsing
                # (numeric for regression, raw string for classification).
                labf.write(f"{lab_str}\n")
                if namef is not None:
                    namef.write(f"{name}\n")
                n_written += 1
        finally:
            if fa is not None:
                fa.close()
            labf.close()
            if namef is not None:
                namef.close()

    if n_written == 0:
        print(f"ERROR: no data rows in {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.no_fasta:
        print(
            f"Wrote {n_written} records to {labels_path} + {names_path}",
            file=sys.stderr,
        )
    else:
        print(
            f"Wrote {n_written} records to {fasta_path} + {labels_path}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
