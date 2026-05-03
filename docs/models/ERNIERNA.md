# ERNIE-RNA

Extract structure-aware RNA embeddings using a pretrained language model with 2D structural bias.

- **Paper:** [Nature Communications 2025](https://www.nature.com/articles/s41467-025-64972-0)
- **Upstream:** https://github.com/Bruce-ywj/ERNIE-RNA
- **License:** MIT
- **Device:** CPU or GPU (~86M params, 12 layers, 768-d embeddings)

## What it does

ERNIE-RNA is a BERT-style RNA language model that incorporates 2D base-pairing potential into the attention mechanism. During pretraining, it learns representations informed by RNA secondary structure. It produces 768-dimensional per-token and per-sequence embeddings that can be used for downstream tasks including secondary structure prediction, 3D closeness prediction, and mean ribosome loading (MRL) estimation.

This module extracts **embeddings** (the foundation model use case). The upstream repo also provides fine-tuned checkpoints for SS prediction, 3D closeness, and MRL, which could be exposed as separate outputs in the future.

## Input format

FASTA file of RNA sequences (A, C, G, U alphabet; T is auto-converted to U).

**Maximum sequence length: 1022 nt.** Longer sequences are truncated with a warning.

Example (reuses `tests/data/rnafm_test.fa`):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGGGAAGUCCUCGUGUUGCACCUGACUGUCUUUCCGAACGGGCGUUUCUUUUCCUCCGCGCUACCUGCCAGG
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUUAAGCUGUAAGAUGGCAGUAGCUUACUAGGCAGGAAAAGACCCUGUUGAGCUUGACUCUAGUU
```

## Output format

A directory containing:

- **`sequence_embeddings.npy`**: NumPy array of shape `(N, 768)` — CLS token embedding per sequence
- **`labels.txt`**: one FASTA header per line

With `--per-token`:
- **`<label>_tokens.npy`**: per-sequence NumPy array of shape `(L, 768)` — one embedding per nucleotide

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-ernierna:latest \
  ernierna_predict.py -i /data/input.fa -o /out
```

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --ernierna_input /path/to/input.fa
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/ernierna/ernierna_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--ernierna_per_token` | `false` | Also output per-token (L x 768) embeddings per sequence |

## Comparison with other foundation models

| Model | Params | Embed dim | Max length | Structure-aware | License |
|-------|--------|-----------|------------|-----------------|---------|
| RNA-FM | 99M | 640 | 1022 | No | MIT |
| RiNALMo | 650M | 1280 | No hard limit | No | Apache-2.0 |
| **ERNIE-RNA** | **86M** | **768** | **1022** | **Yes (2D bias)** | **MIT** |

ERNIE-RNA's key differentiator is the structural bias injected into attention — it computes a base-pairing potential matrix for each input and uses it to modulate attention weights.

## Technical notes

- Built on fairseq 0.12.2 (requires pinned hydra-core/omegaconf versions)
- Pretrained weights (~1 GB) downloaded from Google Drive at build time
- The 2D structural bias computation is O(L^2), so longer sequences are slower
- Additional fine-tuned checkpoints for SS prediction, 3D closeness, and MRL are available in the upstream repo but not exposed in this module

## Fine-tuning (linear probe)

For supervised tasks on user-labeled data, RNA-Zoo exposes a **linear-probe fine-tune** for ERNIERNA: the backbone stays frozen, and a small MLP head trains on top of the 768-d embeddings. This is the de facto standard for foundation models — same pattern Orthrus and HydraRNA use upstream. Backbone fine-tuning is out of scope here (separate per-model design; UTR-LM's pattern is the closest existing reference but only feasible for small backbones).

### Input format

TSV or CSV with required columns `name`, `sequence`, and a numeric label column. Example:

```
name<TAB>sequence<TAB>te
seq_001<TAB>GGGUGCGAU...<TAB>1.42
seq_002<TAB>AUUCCGAGA...<TAB>0.87
```

### Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu  # or gpu — single image \
  --ernierna_finetune_input my_labels.tsv \
  --ernierna_finetune_label te
```

Device: CPU or GPU (single image; uses the inference image).

Outputs land in `results/ernierna_finetune/ernierna_finetune_out/`:

- **`best_head.pt`** — trained MLP head (state_dict + config dict including label mean/std for inverse-transform at predict time)
- **`predictions.tsv`** — predictions for every input row, with `train`/`val` split annotation
- **`metrics.json`** — overall + train + val MSE / R² / Pearson r / Spearman r

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--ernierna_finetune_label` | (required) | Column name in input TSV/CSV |
| `--ernierna_finetune_epochs` | 20 | Max training epochs (early-stop patience 5) |
| `--ernierna_finetune_lr` | 1e-3 | Adam learning rate |

### Fine-tune from precomputed embeddings (skip predict)

If you've already run inference and saved `sequence_embeddings.npy`, you can skip the backbone forward pass and feed those embeddings directly into the head trainer — useful when iterating on head training (different epochs / lr / labels) without re-paying the predict cost.

```bash
nextflow run main.nf -profile docker,cpu \
  --ernierna_finetune_input my_labels.tsv \
  --ernierna_finetune_label te \
  --ernierna_finetune_embeddings my_embeddings.npy
```

When `--ernierna_finetune_embeddings` is set, the workflow skips `ernierna_predict.py` and uses the supplied `(N, D)` `.npy` directly. The TSV still supplies `name` and the label column; the `sequence` column is optional and ignored. Row order in the `.npy` must match row order in the TSV — the head trainer exits with an error if shapes disagree.

Outputs land in the same `ernierna_finetune_out/` directory with the same files (`best_head.pt`, `predictions.tsv`, `metrics.json`) as the full-chain mode.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--ernierna_finetune_embeddings` | `null` | Optional precomputed `(N, D)` `.npy`; when set, skips predict |
| `--ernierna_finetune_head_type` | `linear` | `linear` (strict probe), `mlp` (2-layer), or `xgboost` (requires `_embeddings`) |
| `--ernierna_finetune_task` | `auto` | `auto`, `regression`, or `classification`; auto-detects from labels |
