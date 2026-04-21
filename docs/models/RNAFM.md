# RNA-FM

Extract general-purpose RNA embeddings from sequence using a pretrained foundation model.

- **Paper:** [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00836-4)
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
