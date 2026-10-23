# mRNABERT

Extract embeddings of mRNAs, with one token per UTR nucleotide and one per CDS codon.

- **Paper:** [Nature Communications 2025](https://doi.org/10.1038/s41467-025-65340-8)
- **Upstream:** https://github.com/yyly6/mRNABERT; weights and model code: Hugging Face [`YYLY66/mRNABERT`](https://huggingface.co/YYLY66/mRNABERT)
- **License:** Apache-2.0 (code and weights, per the Hugging Face model card)
- **Device:** CPU or GPU (images `rnazoo-mrnabert-cpu` and `rnazoo-mrnabert`).

## What it does

mRNABERT is a 12-layer BERT-style encoder (width 768, 113.4 million parameters) that uses ALiBi
attention biases instead of position embeddings. It was pretrained by masked language modeling
on about 18 million mRNA sequences, then aligned with protein embeddings by contrastive learning
on 500,000 CDS and protein pairs. The wrapper returns one 768-d embedding per sequence, the mean
over its tokens, and optionally one per token.

## Input

FASTA of mRNA sequences, with T or U. The wrapper uppercases them, turns U into T and picks the
CDS itself: the longest ORF that runs from an ATG to the first in-frame stop codon. The ORF is
tokenized as codons and the rest as single nucleotides; a sequence without an ORF is read as all
UTR. The wrapper logs the ORF it picked for each sequence. Sequences over 1,022 tokens (1,024
with `[CLS]` and `[SEP]`) are truncated with a warning; empty sequences are skipped.

Example (`tests/data/rnafm_test.fa`, used by the test profile; sequences shortened; only
`test_rna_2` has an ORF):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGG...
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUU...
```

## Output

In `mrnabert_out/`:

- `sequence_embeddings.npy`: shape `(N, 768)`, one row per sequence (`[CLS]` and `[SEP]` excluded
  from the mean)
- `labels.txt`: the FASTA headers, in row order
- with per-token output: `<header>_tokens.npy`, shape `(T, 768)` for T tokens, including `[CLS]`
  (first row) and `[SEP]` (last row). Spaces and `/` in the header become `_`.

The model card's example averages over all tokens, `[CLS]` and `[SEP]` included; pool the
per-token output to match it.

Example, for the input above:

```python
import numpy as np
emb = np.load("mrnabert_out/sequence_embeddings.npy")       # shape (2, 768)
names = open("mrnabert_out/labels.txt").read().splitlines()  # ['test_rna_1', 'test_rna_2']
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-mrnabert-cpu:latest \
  mrnabert_predict.py -i /data/input.fa -o /out
```

For the GPU image, use `rnazoo-mrnabert:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
Add `--per-token` for per-token embeddings.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --mrnabert_input /path/to/input.fa
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/mrnabert/mrnabert_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--mrnabert_input` | `null` | FASTA file |
| `--mrnabert_per_token` | `false` | Also write per-token embeddings |
| `--mrnabert_max_tokens` | `1024` | Maximum tokens, `[CLS]` and `[SEP]` included (ALiBi sets no hard limit; the paper tested 3,066) |

## Fine-tuning

Train a linear, MLP or XGBoost head on frozen mRNABERT embeddings, as the [Fine Tuning
guide](../finetuning.md) describes. Its [common parameters](../finetuning.md#common-parameters)
take the prefix `mrnabert`: `--mrnabert_finetune_input` and `--mrnabert_finetune_label` are
required, and `--mrnabert_finetune_embeddings` reuses saved embeddings.

## Limitations

- The CDS is chosen by ORF length alone, and CDS coordinates cannot be supplied: a longer spurious
  ORF wins over the true CDS.
- Both images use plain PyTorch attention: the GPU image disables upstream's Triton kernel,
  which does not compile there. Warnings at load about Triton and the uninitialized pooler are
  expected; the wrapper does not use the pooler.
