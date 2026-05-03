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

## Fine-tuning (linear probe)

For supervised tasks on user-labeled data, RNA-Zoo exposes a **linear-probe fine-tune** for PlantRNAFM: the backbone stays frozen, and a small MLP head trains on top of the 480-d embeddings. This is the de facto standard for foundation models — same pattern Orthrus and HydraRNA use upstream. Backbone fine-tuning is out of scope here (separate per-model design; UTR-LM's pattern is the closest existing reference but only feasible for small backbones).

### Input format

TSV or CSV with required columns `name`, `sequence`, and a numeric label column. Example:

```
name<TAB>sequence<TAB>te
seq_001<TAB>GGGUGCGAU...<TAB>1.42
seq_002<TAB>AUUCCGAGA...<TAB>0.87
```

### Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu # or gpu \
  --plantrnafm_finetune_input my_labels.tsv \
  --plantrnafm_finetune_label te
```

Device: CPU or GPU (uses the inference image). The fine-tune reuses the inference image — no new Docker image to pull.

Outputs land in `results/plantrnafm_finetune/plantrnafm_finetune_out/`:

- **`best_head.pt`** — trained MLP head (state_dict + config dict including label mean/std for inverse-transform at predict time)
- **`predictions.tsv`** — predictions for every input row, with `train`/`val` split annotation
- **`metrics.json`** — overall + train + val MSE / R² / Pearson r / Spearman r

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--plantrnafm_finetune_label` | (required) | Column name in input TSV/CSV |
| `--plantrnafm_finetune_epochs` | 20 | Max training epochs (early-stop patience 5) |
| `--plantrnafm_finetune_lr` | 1e-3 | Adam learning rate |
