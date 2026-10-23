# UTR-LM

Predict mean ribosome loading, translation efficiency or expression level from 5' UTR sequences.

- **Paper:** [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00823-9)
- **Upstream:** https://github.com/a96123155/UTR-LM
- **License:** GPL-3.0
- **Device:** CPU or GPU (images `rnazoo-utrlm-cpu` and `rnazoo-utrlm`).

## What it does

UTR-LM is a 6-layer transformer (1.2 million parameters with the MRL head) pretrained on 5'
UTRs, including 214,349 Ensembl 5' UTRs from human, rat, mouse, chicken and zebrafish. A small
head reads the embedding of the start token:

| Task | Predicts | Scored part of each UTR | Head trained on |
|------|----------|-------------------------|-----------------|
| `mrl` | Mean ribosome loading | Last 50 nt | Synthetic 50-nt 5' UTR libraries |
| `te` | Log translation efficiency (Ribo-seq over RNA-seq RPKM) | Last 100 nt | HEK293T, PC3 or human muscle (`--utrlm_cell_line`) |
| `el` | Log expression level (RNA-seq RPKM) | Last 100 nt | Same three |

## Input

FASTA of 5' UTRs; U becomes T. Only the last 50 nt (`mrl`) or 100 nt (`te`, `el`) of each
sequence are scored; shorter sequences are scored whole.

Example (from `tests/data/utrlm_test.fa`):

```
>synthetic_utr_1
AATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAA
>synthetic_utr_3
ATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATG
```

## Output

`utrlm_out/predictions.tsv`: `header`, `sequence` (the scored part) and one prediction column,
`mean_ribosome_loading`, `translation_efficiency_log` or `expression_level_log`.

Example, `mrl` task (the 51-nt `synthetic_utr_3` loses its first base):

```
header	sequence	mean_ribosome_loading
synthetic_utr_1	AATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAA	8.053340
synthetic_utr_3	TGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATG	6.575327
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-utrlm-cpu:latest \
  utrlm_predict.py -i /data/input.fa -o /out --task mrl --model-dir /opt/utrlm/Model
```

For the GPU image, use `rnazoo-utrlm:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
For `te` or `el`, add `--cell-line HEK`, `pc3` or `Muscle`. Prediction uses cross-validation
fold 0; `--folds all` averages the 10 folds of `te` and `el` (`mrl` ships fold 0 only).

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --utrlm_input /path/to/input.fa --utrlm_task mrl
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/utrlm/utrlm_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--utrlm_input` | `null` | FASTA of 5' UTRs |
| `--utrlm_task` | `mrl` | `mrl`, `te` or `el` |
| `--utrlm_cell_line` | `HEK` | `HEK`, `pc3` or `Muscle`; used by `te` and `el` |
| `--utrlm_checkpoint` | `null` | Absolute path to a fine-tuned `.pt`, used instead of the bundled weights |

## Fine-tuning on your own data

Trains the backbone and head on a table with a `utr` column and a numeric label column (read as
tab-separated only if the file name ends in `.tsv`, otherwise as CSV):

```bash
nextflow run main.nf -profile docker,cpu \
  --utrlm_finetune_input my_training_data.csv \
  --utrlm_finetune_label my_mrl \
  --utrlm_finetune_task mrl
```

The weights with the lowest validation loss are kept. Outputs in
`results/utrlm_finetune/utrlm_finetune_out/`: `best_model.pt` and `predictions.tsv` (the input
table plus a `predicted` column, for all rows). To predict with the checkpoint, pass its
absolute path as `--utrlm_checkpoint` with the same `--utrlm_task`.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--utrlm_finetune_input` | `null` | Training table |
| `--utrlm_finetune_label` | `null` (required) | Label column |
| `--utrlm_finetune_task` | `mrl` | `mrl`, `te` or `el`; sets the backbone variant and scored length |
| `--utrlm_finetune_epochs` | `100` | Maximum epochs |
| `--utrlm_finetune_patience` | `20` | Early-stopping patience (epochs) |
| `--utrlm_finetune_lr` | `0.01` | Adam learning rate |
| `--utrlm_finetune_batch_size` | `32` | Batch size |
| `--utrlm_finetune_val_frac` | `0.2` | Fraction of rows held out for validation |
| `--utrlm_finetune_pretrained` | `null` | Checkpoint to start from; without it, training starts from random weights |

**Known issue:** fine-tuning fails at the first batch (`ValueError: not enough values to unpack
(expected 4, got 2)`): `bin/utrlm_finetune.py` gives UTR-LM's batch converter two fields per
sequence instead of four. The [head trainer](../finetuning.md) on foundation-model embeddings is
an alternative.

## Limitations

- Predictions are computed in order of scored length but written in input order, so they can
  land on the wrong names when scored lengths differ (sequences under 50 nt for `mrl`, under
  100 nt for `te` and `el`). To avoid this, order the FASTA from shortest to longest.
- For `el` with `Muscle`, two checkpoints match each fold; the wrapper takes whichever the file
  system lists first.
