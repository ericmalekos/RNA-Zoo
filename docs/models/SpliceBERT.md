# SpliceBERT

Extract RNA embeddings from a BERT model pretrained on vertebrate primary RNA (pre-mRNA) sequences.

- **Paper:** [Briefings in Bioinformatics 2024](https://doi.org/10.1093/bib/bbae163)
- **Upstream:** https://github.com/biomed-AI/SpliceBERT
- **License:** BSD-3-Clause (code), CC BY 4.0 (weights, [Zenodo 7995778](https://doi.org/10.5281/zenodo.7995778)); both allow public Docker redistribution.
- **Device:** CPU or GPU (images `rnazoo-splicebert-cpu` and `rnazoo-splicebert`).

## What it does

SpliceBERT is a 6-layer BERT encoder (width 512, 16 attention heads, 19.4 million parameters)
pretrained by masked language modeling on over 2 million primary RNA sequences, introns
included, from 72 vertebrates. The image holds the `SpliceBERT.1024nt` checkpoint. The wrapper
returns one 512-d embedding per sequence, the mean over its nucleotide positions, and optionally
one per nucleotide.

## Input

FASTA. Letters are uppercased and U becomes T, since the model was trained on DNA letters.
Sequences over 1,024 nt are truncated with a warning (the model has 1,026 positions, two of them
for the start and end tokens); empty sequences are skipped. Upstream warns that the model may
not work on sequences shorter than 64 nt, the shortest length in its pretraining.

Example (`tests/data/splicebert_test.fa`, sequences shortened):

```
>splicebert_test_1_exon_intron_exon
CAGAGCAGACAACUAAGUGCUAUCAACUAGGC...
>splicebert_test_4_short
GCAACACACCGUAUCGGUCCUAGGAGGUCUGC...
```

## Output

In `splicebert_out/`:

- `sequence_embeddings.npy`: shape `(N, 512)`, one row per sequence
- `labels.txt`: the FASTA headers, in row order
- with per-token output: `<header>_tokens.npy`, shape `(L, 512)`, for each sequence (spaces and
  `/` in the header become `_`)

Example, for the four sequences in `tests/data/splicebert_test.fa`:

```python
import numpy as np
emb = np.load("splicebert_out/sequence_embeddings.npy")       # shape (4, 512)
names = open("splicebert_out/labels.txt").read().splitlines()  # ['splicebert_test_1_exon_intron_exon', ...]
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-splicebert-cpu:latest \
  splicebert_predict.py -i /data/input.fa -o /out
```

For the GPU image, use `rnazoo-splicebert:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
Add `--per-token` for per-nucleotide embeddings.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --splicebert_input /path/to/input.fa
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/splicebert/splicebert_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--splicebert_input` | `null` | FASTA file |
| `--splicebert_per_token` | `false` | Also write per-nucleotide embeddings |
| `--splicebert_max_len` | `1024` | Truncate longer sequences to this many nt |
| `--splicebert_batch_size` | `8` | Sequences per forward pass; lower it if GPU memory runs out |

## Limitations

- Pretraining used vertebrate sequences only.
- Only embeddings are exposed: upstream's splice-site and branchpoint prediction examples are not
  wired in, and RNA-Zoo has no fine-tuning flags for SpliceBERT.
- A warning at load time that the pooler weights are newly initialized is expected; the wrapper
  does not use the pooler.
