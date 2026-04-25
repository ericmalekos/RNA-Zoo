# Quick Start

> Examples below use `-profile docker,gpu`. Swap `gpu` → `cpu` if you don't have an NVIDIA GPU; foundation/structure models will still run on CPU, just slower (~30–60 s per inference call vs sub-second on GPU). seq2ribo and Orthrus are GPU-only and auto-skip under `cpu`.

## How it works

RNAZoo is **opt-in** — only models you provide input for will run. No `--ignore_*` flags needed.

```bash
# Only RNA-FM runs (everything else is skipped automatically)
nextflow run . -profile docker,gpu --rnafm_input my_sequences.fa
```

## Run a single model

### RNA embeddings (RNA-FM)

```bash
nextflow run . -profile docker,gpu \
  --rnafm_input my_rna_sequences.fa
```

### Translation efficiency (RiboNN)

```bash
nextflow run . -profile docker,gpu \
  --ribonn_input my_transcripts.txt
```

### RNA secondary structure (RNAformer)

```bash
nextflow run . -profile docker,gpu \
  --rnaformer_input my_rna_sequences.fa
```

### RNA 3D structure (RhoFold)

```bash
nextflow run . -profile docker,gpu \
  --rhofold_input my_rna_sequences.fa
```

### RNA modifications (MultiRM)

```bash
nextflow run . -profile docker,gpu \
  --multirm_input my_rna_sequences.fa
```

## Run multiple models in parallel

Provide inputs for multiple models and they run simultaneously:

```bash
nextflow run . -profile docker,cpu \
  --rnafm_input sequences.fa \
  --rnaformer_input sequences.fa \
  --spotrna_input sequences.fa \
  --multirm_input sequences.fa
```

## Custom output directories

By default, each model writes to `results/<model_name>/`. Override per-model or globally:

```bash
# Custom per-model output
nextflow run . -profile docker,cpu \
  --rnafm_input sequences.fa \
  --rnafm_outdir my_project/embeddings

# Custom global output root
nextflow run . -profile docker,cpu \
  --rnafm_input sequences.fa \
  --outdir my_project/results
```

## Use a YAML params file

For complex runs, create a YAML file instead of passing many CLI flags. A template is provided at `conf/params_template.yml`:

```bash
cp conf/params_template.yml my_params.yml
# Edit my_params.yml — set _input for models you want to run
nextflow run . -profile docker,cpu -params-file my_params.yml
```

Example `my_params.yml`:

```yaml
outdir: my_results

rnafm_input: data/rna_sequences.fa
rnafm_per_token: true

rnaformer_input: data/rna_sequences.fa
rnaformer_cycling: 6

multirm_input: data/rna_sequences.fa
multirm_alpha: 0.01
```

## Fine-tuning

Some models support fine-tuning on your own data. The workflow is: fine-tune to produce a checkpoint, then use that checkpoint for prediction.

### RiboNN — transfer learning for a new cell type

```bash
# Fine-tune on your TE data
nextflow run . -profile docker,cpu \
  --ribonn_finetune_input my_te_data.tsv \
  --ribonn_finetune_target TE_MyCondition
```

### UTR-LM — fine-tune on custom expression data

```bash
# Step 1: Fine-tune
nextflow run . -profile docker,cpu \
  --utrlm_finetune_input my_utr_data.csv \
  --utrlm_finetune_label my_mrl \
  --utrlm_finetune_task mrl

# Step 2: Predict with fine-tuned model
nextflow run . -profile docker,cpu \
  --utrlm_input new_sequences.fa \
  --utrlm_checkpoint results/utrlm_finetune/best_model.pt \
  --utrlm_task mrl
```

See [RiboNN](../models/RiboNN.md#fine-tuning-on-your-own-data) and [UTR-LM](../models/UTRLM.md#fine-tuning-on-your-own-data) model pages for full details.

## Run with Docker directly (no Nextflow)

Every model can also be run standalone with Docker:

```bash
# RNA-FM embeddings
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rnafm:latest \
  rnafm_predict.py -i /data/input.fa -o /out
```

See each model's page for its specific Docker command.

## Output structure

Results are organized by model name:

```
results/
  ribonn/
    prediction_output.txt
  rnafm/
    rnafm_out/
      sequence_embeddings.npy
      labels.txt
  rnaformer/
    rnaformer_out/
      structures.txt
  ...
```
