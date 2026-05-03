#!/usr/bin/env python3
"""
CLI wrapper for DRfold2 single-sequence ab initio RNA 3D structure prediction.

For each FASTA record, runs the upstream `DRfold_infer.py` pipeline in a
per-sequence subdirectory and copies the final relaxed PDB to the user's
output directory as `<safe_label>.pdb`.

DRfold2's inference is a 4-model deep-learning ensemble (cfg_95/96/97/99)
followed by Selection.py + Optimization.py + Arena. Single-sequence runtime
on a consumer GPU is ~10-30 min for 30-50 nt and scales nonlinearly with
length — see docs/models/DRfold2.md for details.

License: MIT (DRfold2 itself, declared in upstream README body — no LICENSE
file on the repo). Arena is bundled at build time with NO LICENSE on its
upstream — flagged for documentation, not pushed to ghcr until a license
is confirmed.
"""

import argparse
import os
import shutil
import subprocess
import sys

REPO_DIR = "/opt/drfold2_repo"
INFER_SCRIPT = f"{REPO_DIR}/DRfold_infer.py"


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
        description="Predict 3D structures with DRfold2 (single-sequence ab initio)."
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="FASTA file of RNA sequences (A/C/G/U or A/C/G/T)",
    )
    parser.add_argument(
        "-o", "--output", required=True,
        help="Output directory for PDB files (one per input sequence)",
    )
    parser.add_argument(
        "--cluster",
        action="store_true",
        help="Run additional clustering pass to emit alternative models "
             "(produces model_2.pdb, model_3.pdb, … in addition to model_1.pdb). "
             "Doubles or more wall-clock time.",
    )
    parser.add_argument(
        "--keep-intermediate",
        action="store_true",
        help="Keep per-sequence intermediate dirs (rets_dir, folds, relax). "
             "Default removes them after copying the final PDB to save space "
             "(intermediates can be many GB for longer sequences).",
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    sequences = []
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("T", "U")
        if not seq:
            print(f"Warning: {header} has empty sequence, skipping", file=sys.stderr)
            continue
        sequences.append((header, seq))

    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Predicting structures for {len(sequences)} sequences with DRfold2...", file=sys.stderr)

    for header, seq in sequences:
        safe = header.replace("/", "_").replace(" ", "_").replace(":", "_")
        seq_workdir = os.path.join(args.output, f"_drfold2_work_{safe}")
        os.makedirs(seq_workdir, exist_ok=True)

        # Per-sequence FASTA. Upstream needs single-record input; T-form is
        # what DRfold2 expects (its tokenizer maps RNA U → T internally
        # but accepting both is safe).
        fasta_path = os.path.join(seq_workdir, "input.fa")
        with open(fasta_path, "w") as f:
            f.write(f">{safe}\n{seq}\n")

        out_subdir = os.path.join(seq_workdir, "drfold_out")
        os.makedirs(out_subdir, exist_ok=True)

        cmd = ["python", INFER_SCRIPT, fasta_path, out_subdir]
        if args.cluster:
            cmd.append("1")

        print(f"  {header} ({len(seq)} nt): running {' '.join(cmd)}", file=sys.stderr)
        result = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR for {header}:", file=sys.stderr)
            print(result.stdout[-2000:], file=sys.stderr)
            print(result.stderr[-2000:], file=sys.stderr)
            sys.exit(1)

        # Copy primary model PDB. DRfold2 writes <out>/relax/model_*.pdb;
        # model_1.pdb is the top selection.
        relax_dir = os.path.join(out_subdir, "relax")
        if not os.path.isdir(relax_dir):
            print(f"  ERROR for {header}: no relax/ dir produced", file=sys.stderr)
            print(result.stdout[-1000:], file=sys.stderr)
            sys.exit(1)

        pdb_files = sorted(os.listdir(relax_dir))
        pdb_files = [p for p in pdb_files if p.endswith(".pdb")]
        if not pdb_files:
            print(f"  ERROR for {header}: no PDB produced", file=sys.stderr)
            sys.exit(1)

        for pdb in pdb_files:
            src = os.path.join(relax_dir, pdb)
            # model_1.pdb → <safe>.pdb; model_2+.pdb → <safe>_alt2.pdb etc.
            if pdb == "model_1.pdb":
                dst_name = f"{safe}.pdb"
            else:
                # model_N.pdb (N>=2)
                idx = pdb.replace("model_", "").replace(".pdb", "")
                dst_name = f"{safe}_alt{idx}.pdb"
            shutil.copy2(src, os.path.join(args.output, dst_name))

        if not args.keep_intermediate:
            shutil.rmtree(seq_workdir)
        print(f"  {header}: done — wrote {len(pdb_files)} PDB(s)", file=sys.stderr)

    print(f"Done. PDBs written to {args.output}/", file=sys.stderr)


if __name__ == "__main__":
    main()
