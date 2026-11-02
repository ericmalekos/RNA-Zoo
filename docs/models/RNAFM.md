# RNA-FM

Extract general-purpose RNA embeddings from a language model pretrained on non-coding RNA.

- **Paper:** [arXiv 2022](https://arxiv.org/abs/2204.00300)
- **Upstream:** https://github.com/ml4bio/RNA-FM
- **License:** MIT (code), Apache-2.0 (weights)
- **Device:** CPU or GPU (images `rnazoo-rnafm-cpu` and `rnazoo-rnafm`).

## What it does

RNA-FM is a 12-layer transformer encoder (width 640, 99.5 million parameters) pretrained by
masked language modeling on 23 million non-coding RNA sequences from RNAcentral. The wrapper
returns one 640-d embedding per sequence, the mean over its nucleotide positions, and
optionally one per nucleotide.

## Input

FASTA. Letters are uppercased and T becomes U. Sequences over 1,022 nt are truncated with a
warning (the model has 1,024 positions, two of them for the start and end tokens); empty
sequences are skipped.

Example (`tests/data/rnafm_test.fa`, sequences shortened):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGG...
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUU...
```

## Output

In `rnafm_out/`:

- `sequence_embeddings.npy`: shape `(N, 640)`, one row per sequence
- `labels.txt`: the FASTA headers, in row order
- with per-token output: `<header>_tokens.npy`, shape `(L, 640)`, for each sequence (spaces and
  `/` in the header become `_`)

Example, for the input above:

```python
import numpy as np
emb = np.load("rnafm_out/sequence_embeddings.npy")       # shape (2, 640)
names = open("rnafm_out/labels.txt").read().splitlines()  # ['test_rna_1', 'test_rna_2']
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rnafm-cpu:latest \
  rnafm_predict.py -i /data/input.fa -o /out
```

For the GPU image, use `rnazoo-rnafm:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
Add `--per-token` for per-nucleotide embeddings.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --rnafm_input /path/to/input.fa
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/rnafm/rnafm_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--rnafm_input` | `null` | FASTA file |
| `--rnafm_per_token` | `false` | Also write per-nucleotide embeddings |
| `--rnafm_max_len` | `1022` | Truncate longer sequences to this many nt |
| `--rnafm_batch_size` | `8` | Sequences per forward pass; lower it if GPU memory runs out |

## Fine-tuning

Train a linear, MLP or XGBoost head on frozen RNA-FM embeddings, as the [Fine Tuning
guide](../finetuning.md) describes. Its [common parameters](../finetuning.md#common-parameters)
take the prefix `rnafm`: `--rnafm_finetune_input` and `--rnafm_finetune_label` are required, and
`--rnafm_finetune_embeddings` reuses saved embeddings.

## Limitations

- The image holds the non-coding RNA model only; upstream's mRNA-FM (1280-d, trained on coding
  sequences) is not included.
