# DRfold2

Predict RNA 3D structure from a single sequence, without alignments or templates.

- **Paper:** [PLOS Biology 2026](https://doi.org/10.1371/journal.pbio.3003659)
- **Upstream:** https://github.com/leeyang/DRfold2
- **License:** MIT, as stated in the upstream README (the repository has no LICENSE file). The
  model weights carry no license statement, and the bundled [Arena](https://github.com/pylelab/Arena)
  refinement tool declares no license. The RNA-Zoo image is redistributed with the permission of
  the model's authors.
- **Device:** GPU only (image `rnazoo-drfold2`); skipped with a warning under `-profile cpu`.

## What it does

DRfold2 combines a pretrained RNA composite language model (RCLM) with a denoising structure
module. Four configurations of 20 checkpoints each predict end-to-end models and geometry
restraints (334.9 million parameters with the RCLM). A post-processing step selects the best model and
optimizes it with those potentials, and Arena rebuilds the full-atom model. RNA-Zoo runs each
FASTA record as a separate DRfold2 job.

## Input

FASTA. Letters are uppercased and T becomes U; empty sequences are skipped. There is no length
cap; time and memory grow with length.

Example (`tests/data/drfold2_test.fa`, a 24-nt UUCG hairpin):

```
>uucg_hairpin
GAGCGGCAUCUUCGGAUGCCGCUC
```

## Output

In `drfold2_out/`, one PDB per sequence, named after its header (`/`, spaces and `:` become
`_`): `<name>.pdb` is the top model (upstream's `relax/model_1.pdb`). With clustering on, the
alternative models follow as `<name>_alt2.pdb`, `<name>_alt3.pdb` and so on; upstream makes up to
five models in all.

Example, for the input above: `drfold2_out/uucg_hairpin.pdb`, which opens in PyMOL, ChimeraX or
Biopython.

## Run with Docker

```bash
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-drfold2:latest \
  drfold2_predict.py -i /data/input.fa -o /out
```

Add `--cluster` for the alternative models, and `--keep-intermediate` to keep each sequence's
working directory (`_drfold2_work_<name>/` in the output directory).

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,gpu --drfold2_input /path/to/input.fa
```

Results go to `results/drfold2/drfold2_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--drfold2_input` | `null` | FASTA file |
| `--drfold2_cluster` | `false` | Also write alternative models from a clustering pass |
| `--drfold2_keep_intermediate` | `false` | Keep each sequence's working directory; it stays in the Nextflow task directory and is not published |

## Limitations

- An error on any sequence stops the run.
- Upstream's optional OpenMM refinement (`script/refine.py`) is not available: the image has no
  OpenMM.
