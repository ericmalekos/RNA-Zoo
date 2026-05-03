# PlantRNA-FM

Extract RNA embeddings from a plant-only ESM-style transformer trained on ~25M sequences across 1124 plant species.

- **Paper:** [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00946-z) — Yu, Yang et al., "PlantRNA-FM: an interpretable RNA foundation model for exploration of plant transcriptomes"
- **HF model card:** [`yangheng/PlantRNA-FM`](https://huggingface.co/yangheng/PlantRNA-FM)
- **License:** MIT (per HF YAML frontmatter)
- **Device:** CPU or GPU. Two image variants:
    - `rnazoo-plantrnafm:latest` — CUDA-enabled (default, used with `-profile gpu`)
    - `rnazoo-plantrnafm-cpu:latest` — CPU-only (smaller, used with `-profile cpu`)

## What it does

PlantRNA-FM is a 12-layer, 480-dimensional ESM-style transformer pretrained on **plant RNAs only** — ~25M sequences (54.2 billion bases) drawn from 1124 plant species (mosses, ferns, gymnosperms, angiosperms). Architectural details: 35M parameters, 20 attention heads, single-nucleotide tokenization, rotary position embeddings, GeLU activations.

The model card emphasises **interpretability and motif recovery**: the paper reports wet-lab-validated motif discoveries that emerged from the model's attention patterns, an unusual property among RNA foundation models.

The pipeline currently exposes only the inference path (per-sequence and optional per-token embeddings).

## Input format

FASTA file of RNA sequences using RNA alphabet (A, C, G, U). DNA sequences (with T) are automatically converted to U.

**Maximum sequence length: 1024 nt.** PlantRNA-FM has a 1026 max-position-embedding limit; CLS+EOS consume 2 slots, so raw inputs are capped at 1024. Longer sequences are truncated with a warning.

Example (reuses `tests/data/rnafm_test.fa` for the in-pipeline smoke test — the wrapper accepts any RNA character sequence; for real work, plant sequences are recommended since the model was trained plant-only):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGGGAAGUCCUCGUGUUGCACCUGACUGUCUUUCCGAACGGGCGUUUCUUUUCCUCCGCGCUACCUGCCAGG
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUUAAGCUGUAAGAUGGCAGUAGCUUACUAGGCAGGAAAAGACCCUGUUGAGCUUGACUCUAGUU
```

## Output format

A directory containing:

- **`sequence_embeddings.npy`**: NumPy array of shape `(N, 480)` — one 480-d embedding per input sequence (mean-pooled across non-special positions, matching the convention used by RNA-FM / RiNALMo / RNAErnie wrappers; ERNIE-RNA's wrapper is the lone foundation-tier exception and uses [CLS]-pooling instead)
- **`labels.txt`**: one FASTA header per line, in the same order as the embedding rows

With `--per-token`:

- **`<label>_tokens.npy`**: per-sequence NumPy array of shape `(L, 480)` — one 480-d embedding per nucleotide position

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
# CPU
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-plantrnafm-cpu:latest \
  plantrnafm_predict.py -i /data/input.fa -o /out

# GPU
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-plantrnafm:latest \
  plantrnafm_predict.py -i /data/input.fa -o /out
```

Add `--per-token` to either invocation for per-token embeddings.

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu --plantrnafm_input /path/to/input.fa

# GPU
nextflow run main.nf -profile docker,gpu --plantrnafm_input /path/to/input.fa
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/plantrnafm/plantrnafm_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--plantrnafm_per_token` | `false` | Also output per-token (L x 480) embeddings per sequence |
| `--plantrnafm_max_len` | `1024` | Truncate inputs to this many nt (PlantRNA-FM's positional-embedding cap, 1026 minus CLS+EOS) |
| `--plantrnafm_batch_size` | `8` | Sequences per forward pass; lower if you hit GPU OOM |

## Reading the output

```python
import numpy as np

embeddings = np.load("plantrnafm_out/sequence_embeddings.npy")  # (N, 480)
labels = open("plantrnafm_out/labels.txt").read().strip().split("\n")

for label, emb in zip(labels, embeddings):
    print(f"{label}: {emb.shape}")  # (480,)
```

## Comparison with the other foundation models in the zoo

| Model | Embedding | Pooling | Architecture | Training set | Max input | Bundled license |
|-------|-----------|---------|--------------|--------------|-----------|-----------------|
| RNA-FM | 640-d | Mean (excl CLS+EOS) | 12-layer transformer | 23M ncRNAs (RNAcentral) | 1022 nt | MIT |
| RiNALMo | 1280-d | Mean (excl CLS+EOS) | 33-layer transformer (650M params) | 36M ncRNAs (RNAcentral) | ~11k nt (memory-bound) | Apache-2.0 |
| ERNIE-RNA | 768-d | [CLS] | 12-layer + structure-aware attention | 20M ncRNAs (RNAcentral) | 1022 nt | MIT |
| RNAErnie | 768-d | Mean (excl CLS+SEP) | 12-layer transformer + motif-aware MLM | 23M ncRNAs (RNAcentral) | 2046 nt | Apache-2.0 |
| Orthrus | 512-d | Mean (`mean_unpadded`) | Mamba SSM (10M params) | 32.7M mRNAs (GENCODE+RefSeq) | unbounded (linear mem) | MIT |
| **PlantRNA-FM** | **480-d** | **Mean (excl CLS+EOS)** | **12-layer ESM transformer (35M params)** | **~25M plant RNAs (1124 species)** | **1024 nt** | **MIT** |

PlantRNA-FM is the zoo's first **plant-domain** foundation model and the smallest by parameter count. The interpretability angle is its distinguishing feature — the upstream paper anchors several wet-lab-validated motif claims to attention patterns. Useful as a complementary embedding for plant transcriptome work, not a strict upgrade over the general-RNA models for animal sequences.

## Limitations

- **Plant-only training.** Performance on mammalian or bacterial RNA is uncharacterised. For general ncRNA work, prefer RNA-FM, RiNALMo, ERNIE-RNA, or RNAErnie.
- **Maximum input length is 1024 nt** — short ncRNAs and miRNAs fit comfortably; longer mRNAs (>1 kb) must be truncated or chunked. For long mRNAs use Orthrus (Mamba, linear memory).
- **Inference-only currently.** The upstream paper exposes attention-based motif extraction tools; only embedding extraction is wired through this pipeline.

## Fine-tuning

RNAZoo exposes a generic head trainer (linear / MLP / XGBoost, regression or classification) on top of frozen 480-d PlantRNA-FM embeddings. See the [Fine Tuning guide](../finetuning.md) for input format, head choice, the two execution paths (full chain vs. precomputed embeddings), and worked examples.

### PlantRNA-FM-specific parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--plantrnafm_finetune_input` | `null` | TSV/CSV with `name`, `sequence`, label column |
| `--plantrnafm_finetune_label` | (required) | Column name with target values |
| `--plantrnafm_finetune_embeddings` | `null` | Precomputed `(N, D)` `.npy` — switches to the head-only path |
| `--plantrnafm_finetune_head_type` | `linear` | `linear`, `mlp`, or `xgboost` (xgboost requires `_embeddings`) |
| `--plantrnafm_finetune_task` | `auto` | `auto`, `regression`, or `classification` |
| `--plantrnafm_finetune_epochs` | 20 | Max training epochs (torch heads) |
| `--plantrnafm_finetune_lr` | 1e-3 | Adam (torch) or XGBoost learning rate |
