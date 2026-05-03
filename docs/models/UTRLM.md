# UTR-LM

Predict 5'UTR expression metrics: mean ribosome loading, translation efficiency, or expression level.

- **Paper:** [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00823-9)
- **Upstream:** https://github.com/a96123155/UTR-LM
- **License:** GPL-3.0
- **Device:** CPU or GPU (lightweight ~5M parameter model). Two image variants:
    - `rnazoo-utrlm:latest` — CUDA-enabled (default, used with `-profile gpu`)
    - `rnazoo-utrlm-cpu:latest` — CPU-only (smaller, used with `-profile cpu`)

## What it does

UTR-LM is a 5'UTR language model pretrained on RNA sequences from 5 species using masked language modeling with secondary structure and minimum free energy supervision. It predicts expression-related metrics from 5'UTR sequences:

- **MRL** (Mean Ribosome Loading): from synthetic 50-nt UTR library (Sample et al.)
- **TE** (Translation Efficiency): log-transformed, cell-line specific
- **EL** (Expression Level): log-transformed RNA-seq expression, cell-line specific

## Input format

FASTA file of 5'UTR DNA sequences (A, C, G, T alphabet; U is auto-converted to T):

```
>synthetic_utr_1
AATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAA
>synthetic_utr_2
GCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC
```

- **MRL task**: uses 50-nt sequences (last 50 nt if longer)
- **TE/EL tasks**: uses last 100 nt of the 5'UTR

Shorter sequences are automatically padded.

## Output format

**`predictions.tsv`** — one prediction per sequence:

```
header	sequence	mean_ribosome_loading
synthetic_utr_1	AATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAA	8.053340
synthetic_utr_2	GCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC	5.337085
synthetic_utr_3	TGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATG	6.575327
```

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
# CPU — MRL prediction
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-utrlm-cpu:latest \
  utrlm_predict.py -i /data/input.fa -o /out --task mrl --model-dir /opt/utrlm/Model

# GPU — same command, swap image and add nvidia runtime
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-utrlm:latest \
  utrlm_predict.py -i /data/input.fa -o /out --task mrl --model-dir /opt/utrlm/Model
```

For TE/EL prediction add `--task te|el --cell-line HEK|pc3|Muscle`.

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu --utrlm_input /path/to/input.fa --utrlm_task mrl

# GPU
nextflow run main.nf -profile docker,gpu --utrlm_input /path/to/input.fa --utrlm_task mrl
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/utrlm/utrlm_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--utrlm_task` | `mrl` | Prediction task: `mrl`, `te`, or `el` |
| `--utrlm_cell_line` | `HEK` | Cell line for TE/EL tasks: `HEK`, `pc3`, or `Muscle` |

## Available tasks

| Task | Label | Input Length | Cell Lines | Description |
|------|-------|-------------|------------|-------------|
| `mrl` | Mean Ribosome Loading | 50 nt | N/A | From synthetic UTR library |
| `te` | Translation Efficiency (log) | 100 nt | HEK, pc3, Muscle | Cell-line specific |
| `el` | Expression Level (log) | 100 nt | HEK, pc3, Muscle | RNA-seq based |

## Fine-tuning on your own data

> **Known issue (tracked, not yet fixed).** As of 2026-05-03 the fine-tune workflow
> below reaches the training loop but errors during the first batch with
> `ValueError: not enough values to unpack (expected 4, got 2)` from UTR-LM's
> custom ESM `BatchConverter`. The `collate` function in `bin/utrlm_finetune.py`
> emits 2-tuples `(label, seq)` while the upstream fork expects 4-tuples
> `(label, seq, masked_seq, masked_indices)`. A previous PATH-invocation bug
> masked this; that's now fixed (`modules/local/utrlm_finetune.nf` invokes
> `${projectDir}/bin/utrlm_finetune.py`), so the deeper issue is reachable.
> The collate fix is on the backlog — see project notes. The inference (`utrlm_predict.py`)
> and prediction-from-checkpoint paths are unaffected. For supervised tasks on
> 5'UTR sequences in the meantime, the foundation-model
> [head trainer](../finetuning.md) on RNA-FM / RiNALMo / mRNABERT embeddings
> is a working alternative.

UTR-LM can be fine-tuned on your own expression data (MRL, TE, or EL measurements for 5'UTR sequences).

### Input format

CSV or TSV file with columns: `name`, `utr` (5'UTR sequence), and a numeric label column. Example:

```
name,utr,my_mrl
seq1,AATTCCGGAATTCCGG...,5.2
seq2,GCGCGCGCGCGCGCGC...,3.8
```

### Step 1: Fine-tune

```bash
nextflow run main.nf -profile docker,cpu \
  --utrlm_finetune_input my_training_data.csv \
  --utrlm_finetune_label my_mrl \
  --utrlm_finetune_task mrl
```

Output: `utrlm_finetune/best_model.pt` (fine-tuned checkpoint) + `utrlm_finetune/predictions.tsv`.

### Step 2: Predict with fine-tuned model

Use the saved checkpoint for subsequent predictions on new sequences:

```bash
nextflow run main.nf -profile docker,cpu \
  --utrlm_input new_sequences.fa \
  --utrlm_checkpoint utrlm_finetune/best_model.pt \
  --utrlm_task mrl
```

### Fine-tuning parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--utrlm_finetune_label` | (required) | Column name with target values |
| `--utrlm_finetune_task` | `mrl` | Task type: `mrl`, `te`, or `el` (determines backbone + input length) |
| `--utrlm_finetune_epochs` | `100` | Training epochs |
| `--utrlm_finetune_patience` | `20` | Early stopping patience |
| `--utrlm_finetune_lr` | `0.01` | Learning rate |
| `--utrlm_finetune_pretrained` | (none) | Optional: initialize from an existing checkpoint |

## Technical notes

- Uses a custom fork of Facebook's ESM library with RNA-specific alphabet and secondary structure heads.
- Architecture: 6-layer ESM2 transformer (128-d, 16 heads) + linear classification head.
- Weights are bundled in the upstream repo (~1.1 GB total for all tasks/folds).
- MRL has 1 fold; TE/EL have 10 folds each (use `--folds all` for ensemble averaging).
- The model uses the CLS/BOS token embedding for per-sequence prediction.
