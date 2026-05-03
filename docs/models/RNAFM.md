# RNA-FM

Extract general-purpose RNA embeddings from sequence using a pretrained foundation model.

- **Paper:** [arXiv 2022](https://arxiv.org/abs/2204.00300) — "Interpretable RNA Foundation Model from Unannotated Data for Highly Accurate RNA Structure and Function Predictions" (Chen et al.)
- **Upstream:** https://github.com/ml4bio/RNA-FM
- **License:** MIT
- **Device:** CPU or GPU. Two image variants:
    - `rnazoo-rnafm:latest` — CUDA-enabled (default, used with `-profile gpu`)
    - `rnazoo-rnafm-cpu:latest` — CPU-only (smaller, used with `-profile cpu`)

## What it does

RNA-FM is a BERT-style foundation model pretrained on 23 million non-coding RNA sequences. It produces 640-dimensional embeddings for each nucleotide position, which can be used as features for downstream tasks (structure prediction, function annotation, etc.). Per-sequence embeddings are computed by mean-pooling over positions.

## Input format

FASTA file of RNA sequences using RNA alphabet (A, C, G, U). DNA sequences (with T) are automatically converted to U.

**Maximum sequence length: 1022 nt.** RNA-FM has 1024 usable positional slots; BOS/EOS consume 2. Longer sequences are truncated with a warning.

Example (`tests/data/rnafm_test.fa`):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGGGAAGUCCUCGUGUUGCACCUGACUGUCUUUCCGAACGGGCGUUUCUUUUCCUCCGCGCUACCUGCCAGG
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUUAAGCUGUAAGAUGGCAGUAGCUUACUAGGCAGGAAAAGACCCUGUUGAGCUUGACUCUAGUU
```

## Output format

A directory containing:

- **`sequence_embeddings.npy`**: NumPy array of shape `(N, 640)` — one 640-d embedding per input sequence (mean-pooled over positions)
- **`labels.txt`**: one FASTA header per line, in the same order as the embedding rows

With `--per-token`:
- **`<label>_tokens.npy`**: per-sequence NumPy array of shape `(L, 640)` — one 640-d embedding per nucleotide position

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
# CPU
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rnafm-cpu:latest \
  rnafm_predict.py -i /data/input.fa -o /out

# GPU
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rnafm:latest \
  rnafm_predict.py -i /data/input.fa -o /out
```

Add `--per-token` to either invocation for per-token embeddings.

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu --rnafm_input /path/to/input.fa

# GPU
nextflow run main.nf -profile docker,gpu --rnafm_input /path/to/input.fa
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/rnafm/rnafm_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--rnafm_per_token` | `false` | Also output per-token (L x 640) embeddings per sequence |

## Reading the output

```python
import numpy as np

# Per-sequence embeddings
embeddings = np.load("rnafm_out/sequence_embeddings.npy")  # (N, 640)
labels = open("rnafm_out/labels.txt").read().strip().split("\n")

for label, emb in zip(labels, embeddings):
    print(f"{label}: {emb.shape}")  # (640,)

# Per-token embeddings (if --per-token was used)
tokens = np.load("rnafm_out/test_rna_1_tokens.npy")  # (L, 640)
print(f"Per-token shape: {tokens.shape}")
```

## Example output

```
Shape: (2, 640)
Labels:
test_rna_1
test_rna_2
```

Each row is a 640-dimensional vector representing the RNA sequence. These embeddings can be used directly as input features for classifiers, regressors, or clustering.

## Limitations

- Maximum input length is **1022 nucleotides** (1024 positional slots minus 2 for BOS/EOS). Longer sequences are truncated.
- This is the ncRNA model. An mRNA-specific model (mRNA-FM, 1280-d) also exists but is not included in this module.

## Fine-tuning (linear probe)

For supervised tasks on user-labeled data, RNA-Zoo exposes a **linear-probe fine-tune** for RNAFM: the backbone stays frozen, and a small MLP head trains on top of the 640-d embeddings. This is the de facto standard for foundation models — same pattern Orthrus and HydraRNA use upstream. Backbone fine-tuning is out of scope here (separate per-model design; UTR-LM's pattern is the closest existing reference but only feasible for small backbones).

### Input format

TSV or CSV with required columns `name`, `sequence`, and a numeric label column. Example:

```
name<TAB>sequence<TAB>te
seq_001<TAB>GGGUGCGAU...<TAB>1.42
seq_002<TAB>AUUCCGAGA...<TAB>0.87
```

### Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu      # or gpu \
  --rnafm_finetune_input my_labels.tsv \
  --rnafm_finetune_label te
```

Device: CPU or GPU (uses the inference image). The fine-tune reuses the inference image — no new Docker image to pull.

Outputs land in `results/rnafm_finetune/rnafm_finetune_out/`:

- **`best_head.pt`** — trained MLP head (state_dict + config dict including label mean/std for inverse-transform at predict time)
- **`predictions.tsv`** — predictions for every input row, with `train`/`val` split annotation
- **`metrics.json`** — overall + train + val MSE / R² / Pearson r / Spearman r

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--rnafm_finetune_label` | (required) | Column name in input TSV/CSV |
| `--rnafm_finetune_epochs` | 20 | Max training epochs (early-stop patience 5) |
| `--rnafm_finetune_lr` | 1e-3 | Adam learning rate |
