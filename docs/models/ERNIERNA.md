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
| RNA-FM | 99M | 640 | 1024 | No | MIT |
| RiNALMo | 650M | 1280 | No hard limit | No | Apache-2.0 |
| **ERNIE-RNA** | **86M** | **768** | **1022** | **Yes (2D bias)** | **MIT** |

ERNIE-RNA's key differentiator is the structural bias injected into attention — it computes a base-pairing potential matrix for each input and uses it to modulate attention weights.

## Technical notes

- Built on fairseq 0.12.2 (requires pinned hydra-core/omegaconf versions)
- Pretrained weights (~1 GB) downloaded from Google Drive at build time
- The 2D structural bias computation is O(L^2), so longer sequences are slower
- Additional fine-tuned checkpoints for SS prediction, 3D closeness, and MRL are available in the upstream repo but not exposed in this module
