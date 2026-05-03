# RNAErnie

Extract RNA embeddings from a 12-layer ERNIE-framework transformer pretrained with motif-aware multi-level masking and type-guided fine-tuning.

- **Paper:** [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00836-4)
- **Upstream (original PaddlePaddle):** https://github.com/CatIIIIIIII/RNAErnie (MIT)
- **HF port used here:** [`LLM-EDA/RNAErnie`](https://huggingface.co/LLM-EDA/RNAErnie) — official PyTorch port, **Apache-2.0**, 2048-token context
- **License:** Apache-2.0 (weights). RNAErnie's vocab is just A/U/C/G/N + 6 special tokens, so the wrapper bakes a tiny char-level tokenizer in directly and loads weights via `transformers.BertModel.from_pretrained(...)` — no extra packages needed.
- **Device:** CPU or GPU. Two image variants:
    - `rnazoo-rnaernie:latest` — CUDA-enabled (default, used with `-profile gpu`)
    - `rnazoo-rnaernie-cpu:latest` — CPU-only (smaller, used with `-profile cpu`)

## What it does

RNAErnie is a 12-layer, 768-dimensional transformer pretrained on ~23M ncRNA sequences from RNAcentral. Its distinguishing feature is **motif-aware pretraining**: in addition to standard masked language modeling at base and subsequence levels, the pretraining objective also masks RNA motifs from a curated motif database, encouraging the model to learn biologically meaningful k-mer patterns. At fine-tuning time, the paper proposes a **type-guided fine-tuning strategy** where the model first predicts a coarse-grained RNA type (miRNA, lncRNA, etc.) and appends the predicted type as auxiliary information to refine the embedding.

The pipeline currently exposes only the inference path (per-sequence and optional per-token embeddings). Type-guided fine-tuning is a future addition (`TODO` in the fine-tuning support table).

## Input format

FASTA file of RNA sequences using RNA alphabet (A, C, G, U). DNA sequences (with T) are automatically converted to U.

**Maximum sequence length: 2046 nt.** The LLM-EDA port has a 2048 max-position-embedding limit; CLS+SEP consume 2 slots, so raw inputs are capped at 2046. Longer sequences are truncated with a warning.

Example (reuses `tests/data/rnafm_test.fa`):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGGGAAGUCCUCGUGUUGCACCUGACUGUCUUUCCGAACGGGCGUUUCUUUUCCUCCGCGCUACCUGCCAGG
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUUAAGCUGUAAGAUGGCAGUAGCUUACUAGGCAGGAAAAGACCCUGUUGAGCUUGACUCUAGUU
```

## Output format

A directory containing:

- **`sequence_embeddings.npy`**: NumPy array of shape `(N, 768)` — one 768-d embedding per input sequence (mean-pooled across non-special positions, matching the convention used by RNA-FM / RiNALMo / Orthrus wrappers; ERNIE-RNA's wrapper is the lone exception in the zoo and uses [CLS]-pooling instead)
- **`labels.txt`**: one FASTA header per line, in the same order as the embedding rows

With `--per-token`:

- **`<label>_tokens.npy`**: per-sequence NumPy array of shape `(L, 768)` — one 768-d embedding per nucleotide position

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
# CPU
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rnaernie-cpu:latest \
  rnaernie_predict.py -i /data/input.fa -o /out

# GPU
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rnaernie:latest \
  rnaernie_predict.py -i /data/input.fa -o /out
```

Add `--per-token` to either invocation for per-token embeddings.

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu --rnaernie_input /path/to/input.fa

# GPU
nextflow run main.nf -profile docker,gpu --rnaernie_input /path/to/input.fa
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/rnaernie/rnaernie_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--rnaernie_per_token` | `false` | Also output per-token (L x 768) embeddings per sequence |
| `--rnaernie_max_len` | `2046` | Truncate inputs to this many nt (RNAErnie's positional-embedding cap, 2048 minus CLS+SEP) |
| `--rnaernie_batch_size` | `8` | Sequences per forward pass; lower if you hit GPU OOM |

## Reading the output

```python
import numpy as np

embeddings = np.load("rnaernie_out/sequence_embeddings.npy")  # (N, 768)
labels = open("rnaernie_out/labels.txt").read().strip().split("\n")

for label, emb in zip(labels, embeddings):
    print(f"{label}: {emb.shape}")  # (768,)
```

## Comparison with the other foundation models in the zoo

| Model | Embedding | Pooling | Architecture | Training set | Max input | Bundled license |
|-------|-----------|---------|--------------|--------------|-----------|-----------------|
| RNA-FM | 640-d | Mean (excl CLS+EOS) | 12-layer transformer | 23M ncRNAs (RNAcentral) | 1022 nt | MIT |
| RiNALMo | 1280-d | Mean (excl CLS+EOS) | 33-layer transformer (650M params) | 36M ncRNAs (RNAcentral) | ~11k nt (memory-bound) | Apache-2.0 |
| ERNIE-RNA | 768-d | [CLS] | 12-layer + structure-aware attention | 20M ncRNAs (RNAcentral) | 1022 nt | MIT |
| **RNAErnie** | **768-d** | **Mean (excl CLS+SEP)** | **12-layer transformer + motif-aware MLM** | **23M ncRNAs (RNAcentral)** | **2046 nt** | **Apache-2.0** |
| Orthrus | 512-d | Mean (`mean_unpadded`) | Mamba SSM (10M params) | 32.7M mRNAs (GENCODE+RefSeq) | unbounded (linear mem) | MIT |

RNAErnie's unique angle is motif-aware pretraining + the type-guided fine-tuning strategy in the paper. Recent benchmarks place it intermediate on classification and below RiNALMo / ERNIE-RNA on secondary structure — useful as a complementary embedding for ensemble work, not a strict upgrade over what's already in the zoo.

## Limitations

- **Maximum input length is 2046 nt** — short ncRNAs and miRNAs fit comfortably; longer mRNAs (>2 kb) must be truncated or chunked. For long mRNAs use Orthrus (Mamba, linear memory).
- **Inference-only currently.** Type-guided fine-tuning is in upstream and exists as a TODO in the fine-tuning support table.

## Fine-tuning

RNAZoo exposes a generic head trainer (linear / MLP / XGBoost, regression or classification) on top of frozen 768-d RNAErnie embeddings. See the [Fine Tuning guide](../finetuning.md) for input format, head choice, the two execution paths (full chain vs. precomputed embeddings), and worked examples.

### RNAErnie-specific parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--rnaernie_finetune_input` | `null` | TSV/CSV with `name`, `sequence`, label column |
| `--rnaernie_finetune_label` | (required) | Column name with target values |
| `--rnaernie_finetune_embeddings` | `null` | Precomputed `(N, D)` `.npy` — switches to the head-only path |
| `--rnaernie_finetune_head_type` | `linear` | `linear`, `mlp`, or `xgboost` (xgboost requires `_embeddings`) |
| `--rnaernie_finetune_task` | `auto` | `auto`, `regression`, or `classification` |
| `--rnaernie_finetune_epochs` | 20 | Max training epochs (torch heads) |
| `--rnaernie_finetune_lr` | 1e-3 | Adam (torch) or XGBoost learning rate |
