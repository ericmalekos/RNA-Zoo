# Orthrus

Embed mature mRNAs with a Mamba-based foundation model.

- **Paper:** [Nature Methods 2026](https://www.nature.com/articles/s41592-026-03064-3)
- **Upstream:** https://github.com/bowang-lab/Orthrus
- **License:** MIT (code and weights)
- **Device:** GPU only (image `rnazoo-orthrus`, with all seven checkpoints); skipped with a
  warning under `-profile cpu`.

## What it does

Orthrus is a Mamba state-space encoder of mature mRNA, pretrained by contrastive learning on
splice isoforms from ten metazoans and orthologous transcripts from over 400 mammals. The
default checkpoint, `large-4track`, has 6 layers of width 512 (10.2 million parameters). The
wrapper returns one embedding per sequence, the mean over its positions, and optionally one per
nucleotide.

## Variants

Choose a checkpoint with `--orthrus_variant`.

| Variant | Hugging Face repo | Width | Notes |
|---------|-------------------|-------|-------|
| `large-4track` (default) | `quietflamingo/orthrus-large-4-track` | 512 | |
| `4track` | `antichronology/orthrus-4-track` | 512 | Fails at ortholog retrieval and at coding versus noncoding classification |
| `base-4track` | `quietflamingo/orthrus-base-4-track` | 256 | |
| `6track` | `antichronology/orthrus-6-track` | 512 | |
| `small-6track` | `antichronology/orthrus-small-6-track` | 256 | |
| `mlm-6track` | `antichronology/orthrus-mlm-6-track` | 512 | Contrastive plus masked language modeling |
| `large-6track` | `quietflamingo/orthrus-large-6-track` | 512 | |

4-track variants read A, C, G and T as one-hot tracks and need only the FASTA. 6-track variants
also need [annotation](#annotation-input-for-6-track-variants) for two more tracks: a 1 at the
first nucleotide of each CDS codon, and a 1 at the last nucleotide of every exon but the last.

## Input

FASTA (plain or `.gz`) of complete mature mRNAs (5' UTR, CDS and 3' UTR); T or U both work.
There is no length cap and no truncation. The wrapper warns, without refusing, about sequences
shorter than `--orthrus_min_len`.

Example: `tests/data/orthrus_test.fa`, two synthetic mRNAs of 457 and 439 nt.

### Annotation input for 6-track variants

Give one of:

- `--orthrus_annotation`: a TSV (or CSV) with a header row and the columns `name`, `cds_start`
  and `cds_end` (0-based transcript coordinates, end exclusive), plus optional `exon_lengths`
  (comma-separated, in transcript order; without it the splice track is all zeros). `name` is
  the FASTA ID (the header's first word, before any `|`) without a version suffix.
- `--orthrus_gtf`: a GENCODE or Ensembl GTF (plain or `.gz`), from which the wrapper derives
  each transcript's CDS and exon lengths, matching IDs without version suffixes.

If both are given, the TSV is used. Sequences without annotation are skipped with a warning, so
the output can have fewer rows than the FASTA.

```
name	cds_start	cds_end	exon_lengths
tx1	78	1578	78,450,123,50,899
```

## Output

In `orthrus_out/`:

- `sequence_embeddings.npy`: shape `(N, D)`, with D the variant's width (512 or 256)
- `labels.txt`: the FASTA headers, in row order
- with per-token output: `<header>_tokens.npy`, shape `(L, D)`, for each sequence (spaces and
  `/` in the header become `_`)

Example, for `tests/data/orthrus_test.fa` with the default variant:

```python
import numpy as np
emb = np.load("orthrus_out/sequence_embeddings.npy")       # shape (2, 512)
names = open("orthrus_out/labels.txt").read().splitlines()  # full headers: 'test_mrna_1 synthetic ...'
```

## Run with Docker

```bash
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-orthrus:latest \
  orthrus_predict.py -i /data/input.fa -o /out
```

For a 6-track variant, mount the annotation and add, for example,
`--variant 6track --annotation /data/annotation.tsv` (or `--gtf /data/annotation.gtf.gz`).
Add `--per-token` for per-nucleotide embeddings.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,gpu --orthrus_input /path/to/input.fa

# 6-track variant, annotation derived from a GTF
nextflow run main.nf -profile docker,gpu \
  --orthrus_input /path/to/input.fa \
  --orthrus_variant 6track \
  --orthrus_gtf /path/to/gencode.gtf.gz
```

Results go to `results/orthrus/orthrus_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--orthrus_input` | `null` | FASTA file |
| `--orthrus_variant` | `large-4track` | Checkpoint (see [Variants](#variants)) |
| `--orthrus_annotation` | `null` | Annotation TSV for 6-track variants |
| `--orthrus_gtf` | `null` | GTF for 6-track variants |
| `--orthrus_per_token` | `false` | Also write per-nucleotide embeddings |
| `--orthrus_min_len` | `200` | Warn about sequences shorter than this many nt |

## Fine-tuning

Train a linear, MLP or XGBoost head on frozen Orthrus embeddings, as the [Fine Tuning
guide](../finetuning.md) describes. Its [common parameters](../finetuning.md#common-parameters)
take the prefix `orthrus`: `--orthrus_finetune_input` and `--orthrus_finetune_label` are
required, and `--orthrus_finetune_embeddings` reuses saved embeddings. The full chain needs a
GPU (skipped under `-profile cpu`) and always embeds with `large-4track`, whatever
`--orthrus_variant` says. With `--orthrus_finetune_embeddings`, the head trains on CPU in the
`rnazoo-finetune-head` image, so embeddings from any variant work.

## Limitations

- Needs a CUDA GPU; there is no CPU image.
- Orthrus was trained on full mature transcripts; fragments such as CDS-only sequences or single
  exons are out of distribution.
- With `--orthrus_gtf`, a transcript without CDS records gets a CDS track along its whole length.
