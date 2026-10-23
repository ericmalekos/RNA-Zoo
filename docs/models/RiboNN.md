# RiboNN

Predict translation efficiency (TE) from mRNA sequence for 78 human cell types and tissues.

- **Paper:** [Nature Biotechnology 2025](https://www.nature.com/articles/s41587-025-02712-x)
- **Upstream:** https://github.com/Sanofi-Public/RiboNN
- **License:** Sanofi academic, non-commercial license for the code ([LICENSE](https://github.com/Sanofi-Public/RiboNN/blob/main/LICENSE)) and the weights ([MODEL WEIGHTS LICENSE](https://github.com/Sanofi-Public/RiboNN/blob/main/MODEL%20WEIGHTS%20LICENSE.txt)). The grant covers use, copying, modification and merging for academic or non-profit, non-commercial purposes only. The RNA-Zoo image is redistributed with the permission of the model's authors; anyone using it is bound by these terms.
- **Device:** CPU or GPU (images `rnazoo-ribonn-cpu` and `rnazoo-ribonn`).

## What it does

RiboNN is a convolutional network trained on TE from 1,076 human and 835 mouse ribosome
profiling samples with matched RNA-seq. From an mRNA's 5' UTR, CDS and 3' UTR it predicts TE in
all 78 human cell types at once (68 with the mouse model). A human prediction averages 50
models.

## Input

Tab-separated, with a header row and the columns `tx_id`, `utr5_sequence`, `cds_sequence`
(start through stop codon) and `utr3_sequence`. Each CDS must be a multiple of 3 nt and end in
a stop codon, or the run fails. Transcripts over 12,288 nt, or with a 5' UTR over 1,381 nt or a
CDS plus 3' UTR over 11,937 nt, are dropped from the output.

Example (`tests/data/ribonn_prediction_input.txt`, sequences shortened):

```
tx_id	utr5_sequence	cds_sequence	utr3_sequence
ENST00000215375.7	AGACGTCCCTGCGCGTCG...	ATGCTGCCCGCCGCGCTG...	GCGGTGCGTACCCGGTGT...
```

## Output

`ribonn_out/prediction_output.txt`, tab-separated: the input columns, one
`predicted_TE_<cell type>` column per cell type, and `mean_predicted_TE` (the mean over cell
types). Values are on the paper's TE scale, a log-ratio residual, not log2 TE.

Example (sequence columns omitted):

```
tx_id	predicted_TE_HEK293	predicted_TE_HeLa	...	mean_predicted_TE
ENST00000215375.7	1.0705105	1.0321615	...	1.0564895
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.tsv:/data/input.tsv \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-ribonn-cpu:latest \
  bash -c "cd /app && python3 /opt/bin/ribonn_predict.py -i /data/input.tsv -o /out --species human"
```

For the GPU image, use `rnazoo-ribonn:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
For a fine-tuned checkpoint, mount it and add `--checkpoint <file> --target <column>`.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --ribonn_input /path/to/input.tsv
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/ribonn/ribonn_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--ribonn_input` | `null` | Input table |
| `--ribonn_species` | `human` | `human` or `mouse` models; ignored with `--ribonn_checkpoint` |
| `--ribonn_checkpoint` | `null` | Absolute path to a fine-tuned `.ckpt`, used instead of the pretrained models |
| `--ribonn_finetune_target` | `null` | With `--ribonn_checkpoint`: the column the checkpoint was trained on; names the output column |

## Fine-tuning on your own data

Transfer learning from the pretrained human model to one new TE column, such as a new cell type.
The input is the prediction table plus a numeric target column; rows without a value are dropped.

```bash
nextflow run main.nf -profile docker,cpu \
  --ribonn_finetune_input my_training_data.tsv \
  --ribonn_finetune_target TE_MyCondition
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--ribonn_finetune_input` | `null` | Training table |
| `--ribonn_finetune_target` | `null` (required) | Column with the TE values |
| `--ribonn_finetune_phase1_epochs` | `50` | Phase 1: new head on frozen convolution layers |
| `--ribonn_finetune_phase2_epochs` | `150` | Phase 2: all layers, learning rate cut tenfold to 1e-5 |
| `--ribonn_finetune_patience` | `50` | Phase 2 early stopping on validation R² |
| `--ribonn_finetune_folds` | `5` | Cross-validation folds |

Outputs in `results/ribonn_finetune/ribonn_finetune_out/`:

- `predictions.tsv`: `tx_id`, `fold` and `predicted_<target>`, each transcript predicted while held out
- `fold<k>/`: the checkpoint with the best validation R² in fold k

To predict with one of these checkpoints, run the prediction with `--ribonn_checkpoint` (an
absolute path, since the module runs from `/app`) and `--ribonn_finetune_target`. The output then
holds `tx_id` and `predicted_<target>` only.

## Limitations

- Fine-tuning starts from the human model only.
- Fine-tuning is not in the test profile: `conf/test.config` records that it failed on
  `tests/data/ribonn_finetune.tsv` in upstream RiboNN's `validation_step`.
