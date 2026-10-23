# MultiRM

Predict sites of 12 RNA modification types from sequence.

- **Paper:** [Nature Communications 2021](https://doi.org/10.1038/s41467-021-24313-3)
- **Upstream:** https://github.com/Tsedao/MultiRM
- **License:** MIT
- **Device:** CPU or GPU (images `rnazoo-multirm-cpu` and `rnazoo-multirm`).

## What it does

MultiRM scores each position of an RNA for 12 modifications: Am, Cm, Gm and Um (2'-O-methylation),
m1A, m5C, m5U, m6A, m6Am, m7G, Psi (pseudouridine) and AtoI (A-to-I editing). The 51-nt window
around the position is read as 49 overlapping 3-mers (word2vec embeddings) by a bidirectional
LSTM with attention and 12 task heads (2.1 million parameters), trained on 20 base-resolution
epitranscriptome profiles from 15 technologies.

## Input

FASTA. Sequences shorter than 51 nt are skipped with a warning; U becomes T. The first and last
25 nt of each sequence are not scored.

Example (`tests/data/multirm_test.fa`):

```
>test_rna_modification
GGGGCCGTGGATACCTGCCTTTTAATTCTTTTTTATTCGCCCATCGGGGCCGCGGATACCTGCTTTTTATTTTTTTTTCCTTAGCCCATCGGGG
```

## Output

In `multirm_out/`:

- `modification_scores.tsv`: one row per scored position (1-based), with its base and the 12
  probabilities
- `predicted_sites.tsv`: each position and modification with a p-value below the cutoff; the
  p-value is the fraction of upstream's stored null scores (`neg_prob.csv`) above the score
- with plotting on: a heatmap per sequence, `<header>_modifications.png` (`/` and spaces become `_`)

Example rows, from a run on ATF4 (ENST00000674920.3):

```
header	position	base	Am	Cm	Gm	...	m7G	Psi	AtoI
ATF4|ENST00000674920.3	27	G	0.000019	0.000000	0.434129	...	0.373000	0.000266	0.000000

header	modification	position	base	probability	p_value
ATF4|ENST00000674920.3	m6A	601	A	0.693416	0.040000
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-multirm-cpu:latest \
  multirm_predict.py -i /data/input.fa -o /out
```

For the GPU image, use `rnazoo-multirm:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
The wrapper takes `--alpha` (default 0.05) and `--plot`.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --multirm_input /path/to/input.fa
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/multirm/multirm_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--multirm_input` | `null` | FASTA file |
| `--multirm_alpha` | `0.05` | p-value cutoff for `predicted_sites.tsv` |
| `--multirm_plot` | `false` | Also write per-sequence heatmaps |

## Limitations

- Scores differ from those of upstream's `Scripts/main.py`, which transposes the 3-mer input so
  that each score depends only on the window's first 3-mer. The RNA-Zoo wrapper passes the whole
  window.
