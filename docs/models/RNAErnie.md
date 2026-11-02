# RNAErnie

Extract RNA embeddings from RNAErnie, an RNA language model built on the ERNIE framework.

- **Paper:** [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00836-4)
- **Upstream:** https://github.com/CatIIIIIIII/RNAErnie; weights: Hugging Face [`LLM-EDA/RNAErnie`](https://huggingface.co/LLM-EDA/RNAErnie)
- **License:** MIT for the original PaddlePaddle code, which the image does not include; Apache-2.0 for the `LLM-EDA/RNAErnie` weights that it loads.
- **Device:** CPU or GPU (images `rnazoo-rnaernie-cpu` and `rnazoo-rnaernie`).

## What it does

The image runs a PyTorch RNAErnie that the author trained from scratch after the paper: a
12-layer encoder (width 768, 86.6 million parameters) trained on about 31 million RNAcentral
sequences of up to 2,048 tokens, with slightly different tokenization (upstream README). The
paper's model used about 23 million RNAcentral sequences and motif-aware masking. The wrapper
returns one 768-d embedding per sequence (the mean over nucleotides) and optionally one per
nucleotide.

## Input

FASTA. Letters are uppercased, T becomes U, and letters other than A, C, G, U and N become
`[UNK]`. Sequences over 2,046 nt are truncated with a warning (2,048 positions minus `[CLS]`
and `[SEP]`); empty sequences are skipped.

Example (`tests/data/rnaernie_test.fa`, sequences shortened):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGG...
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUU...
```

## Output

In `rnaernie_out/`:

- `sequence_embeddings.npy`: shape `(N, 768)`, one row per sequence
- `labels.txt`: the FASTA headers, in row order
- with per-token output: `<header>_tokens.npy`, shape `(L, 768)`, for each sequence (spaces and
  `/` in the header become `_`)

Example, for the input above:

```python
import numpy as np
emb = np.load("rnaernie_out/sequence_embeddings.npy")       # shape (2, 768)
names = open("rnaernie_out/labels.txt").read().splitlines()  # ['test_rna_1', 'test_rna_2']
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rnaernie-cpu:latest \
  rnaernie_predict.py -i /data/input.fa -o /out
```

For the GPU image, use `rnazoo-rnaernie:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
Add `--per-token` for per-nucleotide embeddings.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --rnaernie_input /path/to/input.fa
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/rnaernie/rnaernie_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--rnaernie_input` | `null` | FASTA file |
| `--rnaernie_per_token` | `false` | Also write per-nucleotide embeddings |
| `--rnaernie_max_len` | `2046` | Truncate longer sequences to this many nt (2,046 at most) |
| `--rnaernie_batch_size` | `8` | Sequences per forward pass; lower it if GPU memory runs out |

## Fine-tuning

Train a linear, MLP or XGBoost head on frozen RNAErnie embeddings, as the [Fine Tuning
guide](../finetuning.md) describes. Its [common parameters](../finetuning.md#common-parameters)
take the prefix `rnaernie`: `--rnaernie_finetune_input` and `--rnaernie_finetune_label` are
required, and `--rnaernie_finetune_embeddings` reuses saved embeddings.

## Limitations

- The embeddings come from the later PyTorch model, not the weights evaluated in the paper.
- The paper's type-guided fine-tuning is not implemented.
