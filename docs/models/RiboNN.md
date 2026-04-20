# RiboNN

Predict translation efficiency (TE) from mRNA sequence across 82 human cell types/tissues.

- **Paper:** [Nature Biotechnology 2025](https://www.nature.com/articles/s41587-025-02712-x)
- **Upstream:** https://github.com/Sanofi-Public/RiboNN
- **License:** Apache 2.0
- **Device:** CPU or GPU (CPU works, GPU faster)

## What it does

RiboNN is a multi-task neural network that predicts translation efficiency from mRNA sequence (5'UTR + CDS + 3'UTR). It outputs TE predictions for 82 human (or mouse) cell types/tissues simultaneously.

## Input format

Tab-separated text file with 4 columns (no header):

```
tx_id    utr5_sequence    cds_sequence    utr3_sequence
```

Example (`tests/data/ribonn_prediction_input.txt`):
```
ENST00000215375.7	AGACGTCCCTGCGCGTCGTCCTCCTCGCCCTCCAGGCCGCCCGCGCCGCGCCGGAGTCCGCTGTCCGCCAGCTACCCGCTTCCTGCCGCCCGCCGCTGCC	ATGCTGCCCGCCGCGCTGCTCCGCCGCCCGGG...	GCGGTGCGTACCCGGTGTCCCGAGGCCCGGCC...
```

Transcripts with combined CDS + 3'UTR length exceeding 11,937 nt are automatically removed.

## Output format

Tab-separated text file (`prediction_output.txt`) with columns:

```
tx_id  utr5_sequence  cds_sequence  utr3_sequence  predicted_TE_108T  predicted_TE_12T  ...  mean_predicted_TE
```

Each `predicted_TE_*` column is the predicted log2 translation efficiency for that cell type. The final column is the mean across all cell types.

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
docker run --rm \
  -v /path/to/input.txt:/app/data/prediction_input1.txt \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-ribonn-cpu:latest \
  bash -c "cd /app && python3 /opt/bin/ribonn_predict.py -i /app/data/prediction_input1.txt -o /out --species human"
```

For mouse: replace `--species human` with `--species mouse`.

To predict using a fine-tuned checkpoint:

```bash
docker run --rm \
  -v /path/to/input.txt:/app/data/prediction_input1.txt \
  -v /path/to/checkpoint.ckpt:/app/checkpoint.ckpt \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-ribonn-cpu:latest \
  bash -c "cd /app && python3 /opt/bin/ribonn_predict.py -i /app/data/prediction_input1.txt -o /out --checkpoint /app/checkpoint.ckpt --target TE_MyCondition"
```

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --ribonn_input /path/to/input.txt
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/ribonn/ribonn_out/prediction_output.txt`.

### Predict with a fine-tuned checkpoint

After fine-tuning (see below), use the saved checkpoint for prediction on new data:

```bash
nextflow run main.nf -profile docker,cpu \
  --ribonn_input /path/to/input.txt \
  --ribonn_checkpoint results/ribonn_finetune/fold0/*.ckpt \
  --ribonn_finetune_target TE_MyCondition
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--ribonn_input` | `null` | Tab-separated input file |
| `--ribonn_species` | `human` | Species for pretrained models (`human` or `mouse`) |
| `--ribonn_checkpoint` | `null` | Path to a fine-tuned `.ckpt` checkpoint for prediction |

## Example output (truncated)

```
tx_id	predicted_TE_HEK293	predicted_TE_HeLa	...	mean_predicted_TE
ENST00000215375.7	1.0705105	1.0321615	...	1.0564895
ENST00000231004.5	0.47455412	0.41119576	...	0.54676294
```

## Fine-tuning on your own data

RiboNN supports transfer learning from the pretrained 78-cell-type human model to a new cell type or condition. The pretrained convolutional layers are frozen initially, then the full model is fine-tuned with a lower learning rate.

### Input format

Tab-separated file with columns: `tx_id`, `utr5_sequence`, `cds_sequence`, `utr3_sequence`, and your target TE column (numeric values). The target column name is specified via `--ribonn_finetune_target`.

### Run fine-tuning

```bash
nextflow run main.nf -profile docker,cpu \
  --ribonn_finetune_input my_training_data.tsv \
  --ribonn_finetune_target TE_MyCondition
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--ribonn_finetune_target` | (required) | Column name containing TE values |
| `--ribonn_finetune_phase1_epochs` | `50` | Epochs for head-only training (conv layers frozen) |
| `--ribonn_finetune_phase2_epochs` | `150` | Epochs for full model training (all layers) |
| `--ribonn_finetune_patience` | `50` | Early stopping patience |
| `--ribonn_finetune_folds` | `5` | Cross-validation folds |

### Output

- `ribonn_finetune/predictions.tsv` — cross-validated predictions on held-out test folds
- `ribonn_finetune/fold*/` — saved model checkpoints per fold
