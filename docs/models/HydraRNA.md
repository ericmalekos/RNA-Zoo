# HydraRNA

Extract embeddings of full-length RNAs from a hybrid state-space and attention language model.

- **Paper:** [Genome Biology 2025](https://doi.org/10.1186/s13059-025-03853-7)
- **Upstream:** https://github.com/GuipengLi/HydraRNA
- **License:** MIT (code and weights)
- **Device:** GPU only (image `rnazoo-hydrarna`); skipped with a warning under `-profile cpu`.

## What it does

HydraRNA has 12 layers of width 1,024 (84 million parameters): bidirectional Hydra state-space
layers, with attention in the 6th and 12th. It was pretrained by masked language modeling on 28
million non-coding RNAs and mRNAs, with sequences over 4,096 nt split into segments. The image
holds the base model from the authors' Zenodo record
[20481998](https://doi.org/10.5281/zenodo.20481998). The wrapper runs it in float16 and returns
one 1024-d embedding per sequence, the mean over its nucleotide positions, and optionally one
per nucleotide.

## Input

FASTA; T becomes U. The model reads at most 10,240 nt per pass, so longer sequences are split
into 10,240 nt chunks and their embeddings averaged. Nothing is truncated.

Example (`tests/data/rnafm_test.fa`, sequences shortened):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGG...
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUU...
```

## Output

In `hydrarna_out/`:

- `sequence_embeddings.npy`: shape `(N, 1024)`, one row per sequence
- `labels.txt`: the FASTA headers, in row order
- with per-token output: `<header>_tokens.npy`, shape `(L, 1024)`, covering at most the first
  10,240 nt (spaces and `/` in the header become `_`)

Example, for the input above:

```python
import numpy as np
emb = np.load("hydrarna_out/sequence_embeddings.npy")       # shape (2, 1024)
names = open("hydrarna_out/labels.txt").read().splitlines()  # ['test_rna_1', 'test_rna_2']
```

## Run with Docker

```bash
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-hydrarna:latest \
  hydrarna_predict.py -i /data/input.fa -o /out
```

Add `--per-token` for per-nucleotide embeddings.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,gpu --hydrarna_input /path/to/input.fa
```

Results go to `results/hydrarna/hydrarna_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--hydrarna_input` | `null` | FASTA file |
| `--hydrarna_per_token` | `false` | Also write per-nucleotide embeddings |
| `--hydrarna_max_len` | `10000` | Print a note for sequences longer than this (no truncation) |

## Fine-tuning

Train a linear, MLP or XGBoost head on frozen HydraRNA embeddings, as the [Fine Tuning
guide](../finetuning.md) describes. Its [common parameters](../finetuning.md#common-parameters)
take the prefix `hydrarna`: `--hydrarna_finetune_input` and `--hydrarna_finetune_label` are
required, and `--hydrarna_finetune_embeddings` reuses saved embeddings. The full chain needs a
GPU (skipped under `-profile cpu`); with `--hydrarna_finetune_embeddings`, the head trains on
CPU in the `rnazoo-finetune-head` image.

## Limitations

- Needs a CUDA GPU; there is no CPU image.
- Chunks are averaged with equal weight, so a short last chunk counts as much as a full one.
- Upstream's `HydraRNA_model_V2.pt` and secondary structure model are not included.
