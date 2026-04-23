# RiNALMo

Extract RNA embeddings from a 650M-parameter RNA language model.

- **Paper:** [NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/RiNALMo)
- **Upstream:** https://github.com/lbcb-sci/RiNALMo
- **License:** Apache 2.0 (code), CC BY 4.0 (weights)
- **Device:** CPU or GPU (650M params — GPU strongly recommended). Two image variants:
    - `rnazoo-rinalmo:latest` — CUDA-enabled (default, used with `-profile gpu`)
    - `rnazoo-rinalmo-cpu:latest` — CPU-only (smaller, used with `-profile cpu`)

## What it does

RiNALMo is a large RNA language model (650M parameters) pretrained on 36 million non-coding RNA sequences using masked language modeling. It produces 1280-dimensional embeddings for each nucleotide position. These embeddings achieve state-of-the-art results on downstream tasks including secondary structure prediction, splice site identification, and RNA family classification.

Compared to RNA-FM (99M params, 640-d), RiNALMo is larger and produces higher-dimensional embeddings but requires more compute.

## Input format

FASTA file of RNA sequences (A, C, G, U). DNA sequences (with T) are automatically converted.

**No architectural length limit** (uses Rotary Position Embeddings) — but attention memory scales O(L²), so practical limits are memory-bound. See [Memory scaling](#memory-scaling) below for exact ceilings on common hardware.

Example (reuses `tests/data/rnafm_test.fa`):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGGGAAGUCCUCGUGUUGCACCUGACUGUCUUUCCGAACGGGCGUUUCUUUUCCUCCGCGCUACCUGCCAGG
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUUAAGCUGUAAGAUGGCAGUAGCUUACUAGGCAGGAAAAGACCCUGUUGAGCUUGACUCUAGUU
```

## Memory scaling

RiNALMo uses full self-attention (no sliding window), so attention memory scales O(L²) with sequence length. With 20 attention heads and float32 attention scores:

    attention_memory = 20 × L² × 4 bytes

Model weights + activations add ~3–4 GB on top.

| Sequence length | Attention matrix | Observed behavior |
|-----------------|------------------|-------------------|
| 1,022 nt        | ~80 MB           | Fits easily on any hardware |
| 3,000 nt        | ~690 MB          | Fits on A10G (24 GB VRAM) |
| 5,000 nt        | ~1.9 GB          | Tight on A10G |
| 11,933 nt       | ~10.6 GB         | OOM on A10G (24 GB) |
| 14,859 nt       | ~16.5 GB         | OOM on A10G |
| 20,635 nt       | ~31.8 GB         | OOM even with 30 GB CPU RAM |

**Practical maximums:**

- A10G (24 GB VRAM): ~2–3k nt
- 30 GB system RAM: ~11k nt
- 64 GB system RAM: ~16k nt

For longer sequences, truncate to a sliding window (e.g. 1022 nt → ~80 MB attention, runnable anywhere).

## Output format

A directory containing:

- **`sequence_embeddings.npy`**: NumPy array of shape `(N, 1280)` — one 1280-d embedding per input sequence (mean-pooled over positions)
- **`labels.txt`**: one FASTA header per line, in the same order as the embedding rows

With `--per-token`:
- **`<label>_tokens.npy`**: per-sequence NumPy array of shape `(L, 1280)` — one 1280-d embedding per nucleotide position

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
# CPU
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rinalmo-cpu:latest \
  rinalmo_predict.py -i /data/input.fa -o /out

# GPU
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rinalmo:latest \
  rinalmo_predict.py -i /data/input.fa -o /out
```

Add `--per-token` to either invocation for per-token embeddings.

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu --rinalmo_input /path/to/input.fa

# GPU (recommended for production)
nextflow run main.nf -profile docker,gpu --rinalmo_input /path/to/input.fa
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/rinalmo/rinalmo_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--rinalmo_per_token` | `false` | Also output per-token (L x 1280) embeddings per sequence |

## Reading the output

```python
import numpy as np

# Per-sequence embeddings
embeddings = np.load("rinalmo_out/sequence_embeddings.npy")  # (N, 1280)
labels = open("rinalmo_out/labels.txt").read().strip().split("\n")

for label, emb in zip(labels, embeddings):
    print(f"{label}: {emb.shape}")  # (1280,)
```

## Example output

```
Shape: (2, 1280)
Labels:
test_rna_1
test_rna_2
```

## Model variants

The giga model (650M params, 1280-d) is the default and only variant included. Smaller variants exist (mega: 150M/640-d, micro: 35M/480-d) but are not bundled.

## Technical notes

- Built from the `non_flash` branch (no FlashAttention dependency — works on any GPU or CPU).
- Weights (~2.6 GB) are baked into the Docker image from Zenodo.
- The same pretrained weights work on both flash and non-flash branches.
- Skipped in the default test profile due to CPU inference time (~60s for model loading).
