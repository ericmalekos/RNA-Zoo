# RhoFold+

Predict RNA 3D structure from sequence (single-sequence mode).

- **Paper:** [Nature Methods 2024](https://doi.org/10.1038/s41592-024-02487-0)
- **Upstream:** https://github.com/ml4bio/RhoFold
- **License:** Apache 2.0
- **Device:** CPU or GPU (CPU is slow — 10 recycling iterations per prediction)

## What it does

RhoFold+ predicts full-atom RNA 3D structures from sequence, similar to AlphaFold for proteins. It combines an RNA language model (RNA-FM, embedded in the architecture) with an E2Eformer structure module and iterative refinement (10 recycling steps). It outputs PDB files with atomic coordinates and per-residue confidence scores (pLDDT).

This module runs in **single-sequence mode** (no MSA databases needed). For higher accuracy with MSA, users can provide a pre-computed A3M file via the upstream CLI.

## Input format

FASTA file of RNA sequences (A, C, G, U alphabet; T is auto-converted):

```
>tRNA_fragment
GCGGAUUUAGCUCAGUUGGGAGAGCGCCAGACUGAAGAUCUGGAGGUCCUGUGUUCGAUCCACAGAAUUCGCACCA
```

**Maximum sequence length: ~1022 nt** (limited by the embedded RNA-FM positional embeddings).

## Output format

Per-sequence output directory containing:

- **`unrelaxed_model.pdb`** — predicted 3D structure in PDB format. B-factor column contains pLDDT confidence scores (0-100).
- **`ss.ct`** — predicted secondary structure in CT (connect table) format
- **`results.npz`** — NumPy archive with distograms, SS probability maps, and pLDDT scores
- **`log.txt`** — inference log with timing

## Run with Docker

```bash
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rhofold:latest \
  rhofold_predict.py -i /data/input.fa -o /out
```

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --rhofold_input /path/to/input.fa
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/rhofold/rhofold_out/<sequence_name>/`.

## Viewing the output

```bash
# View in PyMOL, ChimeraX, or any PDB viewer
pymol results/rhofold/rhofold_out/tRNA_fragment/unrelaxed_model.pdb

# Read pLDDT scores from B-factor column
grep "^ATOM" unrelaxed_model.pdb | awk '{print $6, $11}'
```

## Performance notes

- **CPU:** ~5-15 minutes per sequence (76 nt tRNA). Very slow for long sequences.
- **GPU:** ~1-3 minutes per sequence. Recommended for production use.
- Memory scales quadratically with sequence length (pair representations are L x L x 128).
- Amber energy relaxation is disabled by default (`--relax-steps 0`). Enable with `--relax-steps 1000` if OpenMM is installed.

## Technical notes

- Runs in single-sequence mode by default — no external MSA databases needed
- Weights (~508 MB) baked into Docker image from HuggingFace
- The RNA-FM language model is embedded in the architecture (not a separate module)
- 10 recycling iterations per prediction (each is a full forward pass)
- OpenMM/Amber relaxation is not included in the Docker image to keep it small; the unrelaxed PDB is the primary output
