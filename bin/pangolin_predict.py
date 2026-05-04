#!/usr/bin/env python3
"""
CLI wrapper for Pangolin variant-effect splicing prediction.
Thin pass-through to the upstream `pangolin` console script with
explicit argparse so RNAZoo's Nextflow modules can pass typed flags.

Inputs:
- VCF or CSV of variants
- Reference FASTA (any indexable format pyfastx supports)
- gffutils annotation DB (built from a GTF via upstream `create_db.py`)

Output:
- Annotated VCF/CSV (matching the input format) where each record gains
  a `Pangolin=...` column with `gene|pos:largest_increase|pos:largest_decrease|`
"""

import argparse
import os
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Run Pangolin on a VCF/CSV + reference FASTA + annotation DB"
    )
    parser.add_argument(
        "-i", "--input", "--variant-file", dest="variant_file", required=True,
        help="Input VCF or CSV with variants of interest",
    )
    parser.add_argument(
        "-r", "--reference", "--reference-file", dest="reference_file", required=True,
        help="Reference FASTA (gzipped accepted; pyfastx will index on first read)",
    )
    parser.add_argument(
        "-a", "--annotation", "--annotation-db", dest="annotation_db", required=True,
        help="gffutils annotation database (.db) built from a GTF",
    )
    parser.add_argument(
        "-o", "--output", "--output-prefix", dest="output_prefix", required=True,
        help="Output prefix; final extension matches input (.vcf or .csv)",
    )
    parser.add_argument(
        "-d", "--distance", dest="distance", type=int, default=50,
        help="Bases on either side of the variant for splice-score calculation (default: 50)",
    )
    parser.add_argument(
        "-m", "--mask", dest="mask", choices=["True", "False"], default="True",
        help="Mask gain at annotated sites + loss at unannotated sites (default: True)",
    )
    parser.add_argument(
        "-s", "--score-cutoff", dest="score_cutoff", type=float, default=None,
        help="Output every site with |delta| >= cutoff (default: max-loss/gain only)",
    )
    parser.add_argument(
        "-c", "--column-ids", dest="column_ids", default="CHROM,POS,REF,ALT",
        help="(CSV input only) comma-separated column IDs for chrom/pos/ref/alt",
    )
    args = parser.parse_args()

    pangolin_bin = shutil.which("pangolin")
    if pangolin_bin is None:
        print("Error: 'pangolin' binary not found on PATH. Reinstall the package.", file=sys.stderr)
        sys.exit(1)

    cmd = [
        pangolin_bin,
        args.variant_file,
        args.reference_file,
        args.annotation_db,
        args.output_prefix,
        "-d", str(args.distance),
        "-m", args.mask,
        "-c", args.column_ids,
    ]
    if args.score_cutoff is not None:
        cmd += ["-s", str(args.score_cutoff)]
    print(f"Running: {' '.join(cmd)}", file=sys.stderr)

    out_dir = os.path.dirname(os.path.abspath(args.output_prefix))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    proc = subprocess.run(cmd)
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
