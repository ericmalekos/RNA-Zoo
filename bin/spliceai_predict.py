#!/usr/bin/env python3
"""
CLI wrapper for SpliceAI variant-effect splicing prediction.
Thin pass-through to the upstream `spliceai` console script with explicit
argparse so RNAZoo's Nextflow modules can pass typed flags consistently.

Inputs:
- VCF of variants
- Reference FASTA (must be indexed: a sibling .fai must exist or be creatable)
- Annotation: 'grch37', 'grch38', or a path to a custom GENCODE-style TSV

Output:
- Annotated VCF where the INFO field carries SpliceAI delta scores + positions

License note: the image installs SpliceAI 1.3.1, whose source is GPL-3.0-or-later
and whose bundled weights carry no license statement. Later upstream releases
are PolyForm Strict 1.0.0 (code) and CC BY-NC 4.0 (weights), non-commercial;
Illumina (AI_licensing@illumina.com) licenses them for commercial use. The
RNA-Zoo image is redistributed with the authors' permission.
"""

import argparse
import os
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Run SpliceAI on a VCF + reference FASTA"
    )
    parser.add_argument(
        "-i", "--input", "-I", dest="input_vcf", required=True,
        help="Input VCF with variants of interest",
    )
    parser.add_argument(
        "-o", "--output", "-O", dest="output_vcf", required=True,
        help="Output VCF (annotated with SpliceAI INFO field)",
    )
    parser.add_argument(
        "-r", "--reference", "-R", dest="reference", required=True,
        help="Reference FASTA (a .fai sibling will be created if missing)",
    )
    parser.add_argument(
        "-a", "--annotation", "-A", dest="annotation", default="grch38",
        help="Annotation: 'grch37', 'grch38', or path to a custom GENCODE-style TSV",
    )
    parser.add_argument(
        "-d", "--distance", "-D", dest="distance", type=int, default=50,
        help="Max distance between variant and gained/lost splice site (default: 50)",
    )
    parser.add_argument(
        "-m", "--mask", "-M", dest="mask", type=int, default=0, choices=[0, 1],
        help="Mask annotated gain / unannotated loss (0=raw, 1=masked; default: 0)",
    )
    args = parser.parse_args()

    spliceai_bin = shutil.which("spliceai")
    if spliceai_bin is None:
        print("Error: 'spliceai' binary not found on PATH. Reinstall the package.", file=sys.stderr)
        sys.exit(1)

    cmd = [
        spliceai_bin,
        "-I", args.input_vcf,
        "-O", args.output_vcf,
        "-R", args.reference,
        "-A", args.annotation,
        "-D", str(args.distance),
        "-M", str(args.mask),
    ]
    print(f"Running: {' '.join(cmd)}", file=sys.stderr)

    os.makedirs(os.path.dirname(os.path.abspath(args.output_vcf)) or ".", exist_ok=True)

    proc = subprocess.run(cmd)
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
