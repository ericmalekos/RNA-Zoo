# CaLM

Extract codon-level embeddings of protein-coding sequences.

- **Paper:** [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00791-0)
- **Upstream:** https://github.com/oxpig/CaLM
- **License:** BSD-3-Clause (code). The weights, downloaded from opig.stats.ox.ac.uk, carry no license statement in the repository or the paper, so their commercial use and redistribution are unclear.
- **Device:** CPU or GPU (images `rnazoo-calm-cpu` and `rnazoo-calm`).

## What it does

CaLM is a 12-layer transformer encoder (width 768, rotary positions, 85.7 million parameters)
that reads a coding sequence one codon per token. It was pretrained by masked language modeling
on 9 million non-redundant coding sequences from the European Nucleotide Archive, cropped to
1,024 codons. The wrapper returns one 768-d embedding per sequence (the mean over codons) and
optionally one per codon.

## Input

FASTA of coding sequences. The wrapper reads each sequence as codons from its first base, so
give the CDS alone, in frame: UTRs would be read as codons too. Letters are uppercased and T
becomes U. A length that is not a multiple of 3 is trimmed to the last full codon, and sequences
over 1,024 codons (3,072 nt) are truncated, both with a warning. Empty sequences are skipped.

Example (`tests/data/rnafm_test.fa`, a smoke input rather than real CDSs; the first sequence is
trimmed from 103 to 102 nt):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGG...
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUU...
```

## Output

In `calm_out/`:

- `sequence_embeddings.npy`: shape `(N, 768)`, one row per sequence (`<cls>` and `<eos>` excluded
  from the mean)
- `labels.txt`: the FASTA headers, in row order
- with per-token output: `<header>_tokens.npy`, shape `(C + 2, 768)` for C codons; unlike the
  mean, it keeps `<cls>` (first row) and `<eos>` (last row). Spaces and `/` in the header become `_`.

Example, for the input above:

```python
import numpy as np
emb = np.load("calm_out/sequence_embeddings.npy")       # shape (2, 768)
names = open("calm_out/labels.txt").read().splitlines()  # ['test_rna_1', 'test_rna_2']
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-calm-cpu:latest \
  calm_predict.py -i /data/input.fa -o /out
```

For the GPU image, use `rnazoo-calm:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
Add `--per-token` for per-codon embeddings.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --calm_input /path/to/input.fa
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/calm/calm_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--calm_input` | `null` | FASTA file of coding sequences |
| `--calm_per_token` | `false` | Also write per-codon embeddings |
| `--calm_max_codons` | `1024` | Truncate longer sequences to this many codons |

## Fine-tuning

Train a linear, MLP or XGBoost head on frozen CaLM embeddings, as the [Fine Tuning
guide](../finetuning.md) describes. Its [common parameters](../finetuning.md#common-parameters)
take the prefix `calm`: `--calm_finetune_input` and `--calm_finetune_label` are required, and
`--calm_finetune_embeddings` reuses saved embeddings. Put in-frame coding sequences in the
`sequence` column.

## Limitations

- The wrapper does not locate the CDS; give in-frame coding sequences.
