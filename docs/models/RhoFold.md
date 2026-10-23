# RhoFold+

Predict RNA 3D structure from a single sequence.

- **Paper:** [Nature Methods 2024](https://doi.org/10.1038/s41592-024-02487-0)
- **Upstream:** https://github.com/ml4bio/RhoFold
- **License:** Apache 2.0
- **Device:** CPU or GPU (images `rnazoo-rhofold-cpu` and `rnazoo-rhofold`).

## What it does

RhoFold+ predicts a full-atom 3D structure with a transformer and an invariant point attention
structure module, fed by a built-in RNA-FM language model, over 10 recycling passes (126.9
million parameters). RNA-Zoo runs the single-sequence mode: no MSA is built or read.

## Input

FASTA. Letters are uppercased and T becomes U. Each sequence must be at most 1,022 nt, the limit
of the built-in RNA-FM; the wrapper does not truncate.

Example (`tests/data/rhofold_test.fa`):

```
>tRNA_fragment
GCGGAUUUAGCUCAGUUGGGAGAGCGCCAGACUGAAGAUCUGGAGGUCCUGUGUUCGAUCCACAGAAUUCGCACCA
```

## Output

One directory per sequence, named after the first word of its header (`/` and `:` become `_`):

- `unrelaxed_model.pdb`: the 3D model, with pLDDT × 100 in the B-factor column
- `ss.ct`: the secondary structure (pairs with probability above 0.5)
- `results.npz`: distograms (`dist_n`, `dist_p`, `dist_c`), the base-pair probability map
  (`ss_prob_map`) and per-residue pLDDT from 0 to 1 (`plddt`)
- `log.txt`: the run log

Example, for the input above:

```python
import numpy as np
plddt = np.load("rhofold_out/tRNA_fragment/results.npz")["plddt"][0]  # one value per residue
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rhofold-cpu:latest \
  rhofold_predict.py -i /data/input.fa -o /out
```

For the GPU image, use `rnazoo-rhofold:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --rhofold_input /path/to/input.fa
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/rhofold/rhofold_out/<name>/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--rhofold_input` | `null` | FASTA file |
| `--rhofold_relax_steps` | `0` | Amber relaxation steps; leave at `0` (see Limitations) |

## Limitations

- No Amber relaxation: the images lack OpenMM, so `--rhofold_relax_steps` above 0 makes each
  sequence fail after its unrelaxed outputs are written.
- The PDB B-factors are shifted by one residue (upstream writes each pLDDT on the next residue,
  the last on the first); read per-residue pLDDT from `results.npz`.
- A failed sequence, for example one over 1,022 nt, gets a warning; the others still run.
