# Saluki

Predict mRNA half-life from sequence.

- **Paper:** [Genome Biology 2022](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-022-02811-x)
- **Upstream:** https://github.com/calico/basenji (Saluki model)
- **License:** Apache-2.0 code; CC BY 4.0 weights (Zenodo)
- **Device:** CPU or GPU (images `rnazoo-saluki-cpu` and `rnazoo-saluki`).

## What it does

Saluki is a convolutional and recurrent (GRU) network trained on consensus half-lives of 13,921
human and 14,463 mouse genes. Per nucleotide it reads A, C, G, U, a codon-frame bit (first
nucleotide of each CDS codon) and a splice bit (last nucleotide of each exon). RNA-Zoo averages
50 models. The score is the first principal component of standardized log half-lives: unitless,
not hours or log2 units. Higher means more stable.

## Input

FASTA with the UTRs in lowercase and the CDS in uppercase, named by the first word of the
header. The frame bits are set only if the uppercase span is a multiple of 3 nt. Transcripts over
12,288 nt keep their last 12,288 nt.

```
>tx1
gcgccgagcggcATGCTGTGCGGCCGCTGGTGAcgaccgtctag
```

Recommended: a TSV of exon lengths in transcript order, which sets the splice bits as in
training. They must sum to the sequence length, or the run stops; transcripts without a row get
no splice bits and are listed in a warning.

```
name	exon_lengths
tx1	20,24
```

## Output

In `results/saluki/saluki_out/`, `predictions.tsv` holds one row per transcript: the mean and
standard deviation over the 50 models, and whether exon lengths were given.

```
name	saluki_score_mean	saluki_score_sd	splice_channel_set
```

`preds.npy` holds every model's score, shape `(N, 1, 50)`, in the row order of `names.txt`.

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/exons.tsv:/data/exons.tsv \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-saluki-cpu:latest \
  saluki_predict.py -i /data/input.fa --exons /data/exons.tsv -o /out
```

For the GPU image, use `rnazoo-saluki:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --saluki_input /path/to/input.fa --saluki_exons /path/to/exons.tsv
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/saluki/saluki_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--saluki_input` | `null` | FASTA, UTRs lowercase and CDS uppercase |
| `--saluki_exons` | `null` | Exon-length TSV (`name`, `exon_lengths`); recommended |
| `--saluki_species` | `human` | Output head; only `human` works |

## Limitations

- `--saluki_species mouse` (wrapper `--data-head 1`) fails: the image builds the model with one
  output head, so loading the mouse head raises an `IndexError`.
