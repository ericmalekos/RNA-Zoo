#!/usr/bin/env python3
"""
One-shot subsampler for the Riboformer GSE119104_Mg_buffer dataset.

Takes a directory containing the full Mg_buffer files (146 MB) and writes
a trimmed copy of the first N bp to an output directory. Used to generate
a small external-input test bundle under tests/data/riboformer/.

Extract the source files from the image with:

    SCRATCH=$(mktemp -d)
    docker run --rm -v $SCRATCH:/out \\
        ghcr.io/ericmalekos/rnazoo-riboformer-cpu:latest \\
        bash -c "cp /opt/Riboformer/datasets/GSE119104_Mg_buffer/{NC000913.2.*,GSM*wig} /out/ \\
                 && chown -R $(id -u):$(id -g) /out/"

Then run:

    python3 scripts/subsample_mg_buffer.py $SCRATCH tests/data/riboformer 100000

Trims:
- FASTA: rewrite with only the first N bp of NC_000913.2
- GFF3: keep header lines + features whose end <= N
- Each of 4 WIG files (fixedStep start=1 step=1): keep 2 header lines + first N data lines
"""

import argparse
import sys
from pathlib import Path

WIG_NAMES = [
    "GSM3358138_filter_Cm_ctrl_f.wig",
    "GSM3358138_filter_Cm_ctrl_r.wig",
    "GSM3358140_freeze_Mg_ctrl_f.wig",
    "GSM3358140_freeze_Mg_ctrl_r.wig",
]


def trim_fasta(src: Path, dst: Path, n: int) -> None:
    seq_parts: list[str] = []
    header = None
    with src.open() as f:
        for line in f:
            line = line.rstrip()
            if line.startswith(">"):
                header = line
            else:
                seq_parts.append(line)
    if header is None:
        raise SystemExit(f"{src}: no FASTA header found")
    seq = "".join(seq_parts)[:n]
    with dst.open("w") as f:
        f.write(f"{header}\n")
        # 70-char line width, matches the upstream format
        for i in range(0, len(seq), 70):
            f.write(seq[i : i + 70] + "\n")


def trim_gff3(src: Path, dst: Path, n: int) -> int:
    kept = 0
    with src.open() as f, dst.open("w") as g:
        for line in f:
            if line.startswith("#"):
                g.write(line)
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 5:
                continue
            try:
                end = int(fields[4])
            except ValueError:
                continue
            if end <= n:
                g.write(line)
                kept += 1
    return kept


def trim_wig(src: Path, dst: Path, n: int) -> None:
    # fixedStep WIG: first 2 lines are `track ...` + `fixedStep ...` headers,
    # then one value per position starting at position 1.
    with src.open() as f, dst.open("w") as g:
        header1 = f.readline()
        header2 = f.readline()
        if not header1.startswith("track") or "fixedStep" not in header2:
            raise SystemExit(
                f"{src}: expected 'track ...' + 'fixedStep ...' headers, got:\n"
                f"  {header1!r}\n  {header2!r}"
            )
        g.write(header1)
        g.write(header2)
        for i, line in enumerate(f):
            if i >= n:
                break
            g.write(line)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("src_dir", type=Path, help="Source directory with full Mg_buffer files")
    parser.add_argument("dst_dir", type=Path, help="Output directory for trimmed test bundle")
    parser.add_argument("bp", type=int, help="Number of leading base pairs to keep (e.g. 100000)")
    args = parser.parse_args()

    args.dst_dir.mkdir(parents=True, exist_ok=True)

    fasta_src = args.src_dir / "NC000913.2.fasta"
    gff_src = args.src_dir / "NC000913.2.gff3"
    for f in [fasta_src, gff_src, *(args.src_dir / w for w in WIG_NAMES)]:
        if not f.exists():
            print(f"missing source file: {f}", file=sys.stderr)
            return 1

    print(f"Trimming to first {args.bp:,} bp → {args.dst_dir}/")

    trim_fasta(fasta_src, args.dst_dir / "NC000913.2.fasta", args.bp)
    kept = trim_gff3(gff_src, args.dst_dir / "NC000913.2.gff3", args.bp)
    for name in WIG_NAMES:
        trim_wig(args.src_dir / name, args.dst_dir / name, args.bp)

    # Size report
    total = 0
    for p in sorted(args.dst_dir.iterdir()):
        sz = p.stat().st_size
        total += sz
        print(f"  {p.name:<45} {sz:>10,} bytes")
    print(f"  {'TOTAL':<45} {total:>10,} bytes ({kept} GFF features kept)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
