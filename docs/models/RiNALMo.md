# RiNALMo

Extract RNA embeddings from a 650M-parameter RNA language model.

- **Paper:** [Nature Communications 2025](https://www.nature.com/articles/s41467-025-60872-5)
- **Upstream:** https://github.com/lbcb-sci/RiNALMo
- **License:** Apache-2.0 (code), CC BY 4.0 (weights)
- **Device:** CPU or GPU (images `rnazoo-rinalmo-cpu` and `rnazoo-rinalmo`).

## What it does

RiNALMo is a 33-layer transformer encoder (width 1,280, 650 million parameters, rotary position
embeddings) pretrained by masked language modeling on 36 million non-coding RNA sequences from
RNAcentral and other databases. The image runs the giga model, built from upstream's
`non_flash` branch, which needs no FlashAttention. The wrapper returns one 1280-d embedding per
sequence, the mean over its nucleotide positions, and optionally one per nucleotide.

## Input

FASTA. Letters are uppercased and T becomes U; empty sequences are skipped. There is no length
cap and no truncation.

Example (`tests/data/rnafm_test.fa`, sequences shortened):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGG...
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUU...
```

## Output

In `rinalmo_out/`:

- `sequence_embeddings.npy`: shape `(N, 1280)`, one row per sequence
- `labels.txt`: the FASTA headers, in row order
- with per-token output: `<header>_tokens.npy`, shape `(L, 1280)`, for each sequence (spaces
  and `/` in the header become `_`)

Example, for the input above:

```python
import numpy as np
emb = np.load("rinalmo_out/sequence_embeddings.npy")       # shape (2, 1280)
names = open("rinalmo_out/labels.txt").read().splitlines()  # ['test_rna_1', 'test_rna_2']
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rinalmo-cpu:latest \
  rinalmo_predict.py -i /data/input.fa -o /out
```

For the GPU image, use `rnazoo-rinalmo:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
Add `--per-token` for per-nucleotide embeddings.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --rinalmo_input /path/to/input.fa
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/rinalmo/rinalmo_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--rinalmo_input` | `null` | FASTA file |
| `--rinalmo_per_token` | `false` | Also write per-nucleotide embeddings |
| `--rinalmo_batch_size` | `1` | Sequences per forward pass; kept at 1 to limit memory |

## Fine-tuning

Train a linear, MLP or XGBoost head on frozen RiNALMo embeddings, as the [Fine Tuning
guide](../finetuning.md) describes. Its [common parameters](../finetuning.md#common-parameters)
take the prefix `rinalmo`: `--rinalmo_finetune_input` and `--rinalmo_finetune_label` are
required, and `--rinalmo_finetune_embeddings` reuses saved embeddings.

## Limitations

- Attention memory grows with the square of the sequence length, so long sequences can run out
  of memory.
- The image holds the giga model only; upstream's smaller mega (148M parameters) and micro
  (33.5M) models are not included.
