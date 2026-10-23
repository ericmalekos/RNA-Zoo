# Fine Tuning

The nine RNA foundation models can train a small prediction head on your labeled sequences. The
model itself stays frozen: its embeddings feed a linear, MLP or XGBoost head, for regression or
classification. SpliceBERT, the tenth embedding model, has no fine-tuning parameters. RiboNN,
UTR-LM and RiboTIE fine-tune in their own ways; see
[Other fine-tuning](#other-fine-tuning).

## Supported models

Each model's parameters start with its prefix, for example `--rnafm_finetune_input`.

| Model | Prefix | Embedding width | Embed and train in one run (Path A) |
|-------|--------|-----------------|-------------------------------------|
| [RNA-FM](models/RNAFM.md) | `rnafm` | 640 | CPU or GPU |
| [RiNALMo](models/RiNALMo.md) | `rinalmo` | 1280 | CPU or GPU |
| [ERNIE-RNA](models/ERNIERNA.md) | `ernierna` | 768 | CPU or GPU |
| [Orthrus](models/Orthrus.md) | `orthrus` | 512 | GPU only; always embeds with `large-4track` |
| [HydraRNA](models/HydraRNA.md) | `hydrarna` | 1024 | GPU only |
| [RNAErnie](models/RNAErnie.md) | `rnaernie` | 768 | CPU or GPU |
| [PlantRNA-FM](models/PlantRNAFM.md) | `plantrnafm` | 480 | CPU or GPU |
| [CaLM](models/CaLM.md) | `calm` | 768 | CPU or GPU |
| [mRNABERT](models/mRNABERT.md) | `mrnabert` | 768 | CPU or GPU |

Training on saved embeddings (Path B) runs on the CPU for every model and accepts any width, for
example 256 from an Orthrus `base-4track` run.

## Quick start

```bash
nextflow run main.nf -profile docker,cpu \
  --rnafm_finetune_input my_labels.tsv \
  --rnafm_finetune_label te
```

Results go to `results/rnafm_finetune/rnafm_finetune_out/`. For another model, change the
prefix.

## Input

A table with a header row, tab-separated, or comma-separated if the file name ends in `.csv`. It
needs the columns `name` and `sequence` and the label column named by
`--<prefix>_finetune_label`. An empty name, sequence or label stops the run.

```
name	sequence	te
seq_001	GGGUGCGAU...	1.42
seq_002	AUUCCGAGA...	0.87
```

Labels are treated as classes if any label is not a number, or if all are whole numbers with at
most 10 distinct values; otherwise the task is regression. `--<prefix>_finetune_task regression`
or `classification` overrides this.

## Two ways to run

### Path A: embed and train in one run (default)

The workflow embeds the `sequence` column with the model's own image, then trains the head. It
supports the `linear` and `mlp` heads.

### Path B: train on saved embeddings

Give the `sequence_embeddings.npy` of an earlier run with `--<prefix>_finetune_embeddings`. The
workflow then skips the model and trains the head in the CPU-only `rnazoo-finetune-head` image.
All three heads work, and the `sequence` column is not needed.

```bash
# 1. Embed once; my_seqs.fa holds the table's sequences in the table's order
nextflow run main.nf -profile docker,cpu --rnafm_input my_seqs.fa --outdir results_emb

# 2. Train heads on the saved embeddings, as often as needed
nextflow run main.nf -profile docker,cpu \
  --rnafm_finetune_input my_labels.tsv \
  --rnafm_finetune_label te \
  --rnafm_finetune_embeddings results_emb/rnafm/rnafm_out/sequence_embeddings.npy \
  --rnafm_finetune_head_type xgboost
```

The rows of the `.npy` must be the table's rows, in the same order. The trainer checks only that
the two have the same number of rows.

## Heads

Set with `--<prefix>_finetune_head_type`.

| Head | Architecture | Runs in |
|------|--------------|---------|
| `linear` (default) | One linear layer | Path A or B |
| `mlp` | Linear layer to 64 units, ReLU, dropout 0.2, linear output layer | Path A or B |
| `xgboost` | XGBoost, up to 200 trees of depth 6 | Path B only |

The rows are split at random (seed 42) into 80% for training and 20% for validation. The linear
and MLP heads train with Adam in batches of 32 and keep the weights with the lowest validation
loss, stopping after 5 epochs without improvement. XGBoost stops after 10 rounds without
improvement on the validation rows. For the linear and MLP heads, regression labels are
standardized on the training rows, and predictions are returned on the original scale.

## Outputs

In `results/<prefix>_finetune/<prefix>_finetune_out/`:

- `predictions.tsv`: for every row, `name`, `true`, `predicted` and `split` (`train` or `val`);
  classification adds a `prob_<class>` column per class.
- `metrics.json`: metrics for all rows, the training rows and the validation rows. Regression:
  MSE, R², Pearson r and Spearman r. Classification: accuracy, macro and weighted F1, AUROC (two
  classes only), the confusion matrix, and precision, recall and F1 per class.
- `best_head.pt`: the linear or MLP head's weights and settings. An XGBoost head is saved as
  `best_head.ubj`, with its settings in `best_head_config.json`.

## Common parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--<prefix>_finetune_input` | `null` | Labeled table; setting it starts fine-tuning |
| `--<prefix>_finetune_label` | `null` | Label column (required) |
| `--<prefix>_finetune_embeddings` | `null` | Saved `(N, D)` embeddings `.npy`; switches to Path B |
| `--<prefix>_finetune_head_type` | `linear` | `linear`, `mlp` or `xgboost` (Path B only) |
| `--<prefix>_finetune_task` | `auto` | `auto`, `regression` or `classification` |
| `--<prefix>_finetune_epochs` | `20` | Maximum epochs for the linear and MLP heads |
| `--<prefix>_finetune_lr` | `1e-3` | Learning rate, for Adam or XGBoost |
| `--<prefix>_finetune_outdir` | `null` | Output directory; `<outdir>/<prefix>_finetune` when unset |

## Test profiles

```bash
# Path A, regression; also runs the inference test profile
nextflow run main.nf -profile test_finetune,docker,cpu

# Path B, regression
nextflow run main.nf -profile test_finetune_from_emb,docker,cpu

# Path B, classification of two classes
nextflow run main.nf -profile test_finetune_classify,docker,cpu
```

Each covers eight of the nine models (all but HydraRNA) on 30 sequences whose labels follow GC
content; under `cpu`, `test_finetune` skips Orthrus. Path B uses a random embedding file, so the
tests check that every step runs and the metrics are finite, not how well the heads learn.

## Limitations

- Only the head trains; the foundation models cannot be fine-tuned themselves.
- XGBoost needs saved embeddings; without them the workflow stops with an error.
- One label per row; multi-label classification is not supported.
- Classes are not reweighted, so a rare class weighs only as much as its rows.
- There is no hyperparameter search, and the validation fraction, patience and batch size are
  fixed.
- The validation rows also choose when training stops, so they are not an independent test. For
  a held-out test set, run `finetune_head.py --split-file` (one `train` or `test` per row) in the
  `rnazoo-finetune-head` image; the workflow does not pass a split file.
- The head accepts any `(N, D)` array and does not check which model made it.

## Other fine-tuning

- **[RiboTIE](models/RiboTIE.md):** every run fine-tunes the pretrained models on the sample's
  reads before it calls ORFs. `--ribotie_max_epochs` and `--ribotie_patience` control the
  training.
- **[RiboNN](models/RiboNN.md#fine-tuning-on-your-own-data):** transfer learning from the
  pretrained human model to a new TE column, with cross-validation.
- **[UTR-LM](models/UTRLM.md#fine-tuning-on-your-own-data):** trains the model and its head on
  5' UTRs with a numeric label.

RiboNN and UTR-LM fine-tuning currently fail, and neither is in a test profile:
`conf/test.config` records a shape mismatch in upstream RiboNN's validation step and a
batch-format error in the UTR-LM script. A fix is planned for a later release.
