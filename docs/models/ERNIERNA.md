# ERNIE-RNA

Extract structure-aware RNA embeddings from a language model with a base-pairing attention bias.

- **Paper:** [Nature Communications 2025](https://www.nature.com/articles/s41467-025-64972-0)
- **Upstream:** https://github.com/Bruce-ywj/ERNIE-RNA
- **License:** MIT (code). The pretrained weights carry no license statement (the README's
  license sentence names the source code only), so their commercial use and redistribution are
  unclear.
- **Device:** CPU or GPU; one image, `rnazoo-ernierna`, serves both profiles.

## What it does

ERNIE-RNA is a 12-layer BERT-style encoder (width 768, 86 million parameters) whose attention
carries a base-pairing bias. It was pretrained by masked language modeling on 20.4 million
non-coding RNAs from RNAcentral. The wrapper returns a 768-d sequence embedding, the last layer
averaged over the nucleotides, and optionally one embedding per nucleotide.

## Input

FASTA. Letters are uppercased and T becomes U. Sequences over 1,022 nt, the upstream maximum,
are truncated with a warning; empty sequences are skipped.

Example (`tests/data/rnafm_test.fa`, sequences shortened):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGG...
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUU...
```

## Output

In `ernierna_out/`:

- `sequence_embeddings.npy`: shape `(N, 768)`, one row per sequence
- `labels.txt`: the FASTA headers, in row order
- with per-token output: `<header>_tokens.npy`, shape `(L, 768)`, for each sequence (spaces and
  `/` in the header become `_`)

Example, for the input above:

```python
import numpy as np
emb = np.load("ernierna_out/sequence_embeddings.npy")       # shape (2, 768)
names = open("ernierna_out/labels.txt").read().splitlines()  # ['test_rna_1', 'test_rna_2']
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-ernierna:latest \
  ernierna_predict.py -i /data/input.fa -o /out
```

For a GPU, add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all` (same image).
Add `--per-token` for per-nucleotide embeddings and `--pooling cls` for the CLS token
instead of the mean.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --ernierna_input /path/to/input.fa
```

Use `-profile docker,gpu` for a GPU. Results go to `results/ernierna/ernierna_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--ernierna_input` | `null` | FASTA file |
| `--ernierna_per_token` | `false` | Also write per-nucleotide embeddings |
| `--ernierna_max_len` | `1022` | Truncate longer sequences to this many nt |
| `--ernierna_pooling` | `mean` | Sequence embedding: `mean` over nucleotides or `cls` for the CLS token |

## Fine-tuning

Train a linear, MLP or XGBoost head on frozen ERNIE-RNA embeddings, as the [Fine Tuning
guide](../finetuning.md) describes. Its [common parameters](../finetuning.md#common-parameters)
take the prefix `ernierna`: `--ernierna_finetune_input` and `--ernierna_finetune_label` are
required, and `--ernierna_finetune_embeddings` reuses saved embeddings. Embedding and training
in one run uses the pooling that `--ernierna_pooling` sets.

## Limitations

- Before release 1.0.2 the sequence embedding was the CLS token of the second of the 12
  layers: the wrapper passed `layer_idx=1`, which upstream's model reads as an index into its
  layer outputs. That vector records mostly the first nucleotide of the input: on 5,000 human
  and mouse transcripts a linear classifier recovers it for every sequence, and the vectors
  cluster by it. From 1.0.2 every output comes from the last layer, and the default is the mean
  over nucleotides, as for the other RNA Zoo foundation models; `--ernierna_pooling cls` (or
  `--pooling cls` in the container) gives the last layer's CLS token.
- Upstream's secondary structure, 3D closeness and mean ribosome load models are not included.
