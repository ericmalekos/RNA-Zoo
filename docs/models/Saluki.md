# Saluki

Predict mRNA half-life from sequence.

- **Paper:** [Genome Biology 2022](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-022-02811-x)
- **Upstream:** https://github.com/calico/basenji (Saluki model)
- **License:** Apache-2.0 code; CC BY 4.0 weights (Zenodo)
- **Device:** CPU or GPU (a 50-member ensemble; a GPU helps for large inputs). Two image variants:
    - `rnazoo-saluki:latest`: CUDA-enabled (default, used with `-profile gpu`)
    - `rnazoo-saluki-cpu:latest`: CPU-only (smaller, used with `-profile cpu`)

## What it does

Saluki predicts mRNA half-life from sequence with a convolutional and recurrent network. It
reads one mRNA at a time as six channels per nucleotide: A, C, G, U, a codon-frame bit set at
the first nucleotide of every codon of the CDS, and a splice-junction bit set at the last
nucleotide of every exon. The model is an ensemble of 50 cross-validated networks (10 folds by
5 replicates) with human and mouse output heads.

The output is Saluki's **consensus half-life score**: the model was trained on the first
principal component of standardized log half-lives measured across many studies, so the
score is unitless. It is not a half-life in hours and not a log2 half-life. Higher scores
mean more stable transcripts.

## Input format

FASTA file where **lowercase = UTR** and **UPPERCASE = CDS**:

```
>test_transcript_1
gcgccgagcggcgccccgctgccctgtccccgcgtgcagaccccgggcccggccccggccATGCTGTGCGGCCGCTGG
AGGCGTTGCCGCCGCCCCGCCCGAGGAGCCCCCGGTGGCCGCCCAGGTCGCAGCCCAAGTCGCGGCGCCGGTCGCTCT
CCCGTCCCCGCCGACTCCCTCCGATGGCGGCACCAAGAGGCCCGGGCTGCGGGCGCTGAAGAAGATGGGCCTGACGGAG
...CACTCCAACAAcgaccgtctagagggggctgagatcgaggagttcctgcggcggctgctgaagcggccggag
```

- 5' UTR: lowercase at the start
- CDS: UPPERCASE in the middle (start through stop codon)
- 3' UTR: lowercase at the end

A transcript written all in uppercase is read as coding from its first nucleotide, in the
wrong frame and through the 3' UTR; its prediction is not meaningful.

### Exon structure (recommended)

Saluki was trained with the splice-junction channel set. Give the exon lengths of each
transcript, in transcript order, so that the input matches training:

```
name	exon_lengths
test_transcript_1	231,118,140,1622
```

The lengths must sum to the sequence length, and `name` must match the first word of the FASTA
header. Transcripts without a row are predicted with the splice channel at zero, as RNA-Zoo
releases before 1.0.0 did for every transcript, and are listed in a warning. In the RNA-Zoo
paper, setting the channel raised every prediction for eight human mRNAs, by up to 2.4 score
units, and changed their order.

## Output format

In `saluki_out/`:

- `preds.npy`: array of shape `(N, 1, 50)`, N transcripts by 50 ensemble members
- `names.txt`: the transcript names, in row order
- `predictions.tsv`: `name`, `saluki_score_mean`, `saluki_score_sd` (over the 50 members) and
  `splice_channel_set` (whether exon lengths were given)

```python
import numpy as np
preds = np.load("saluki_out/preds.npy")
score = preds.mean(axis=-1).ravel()   # consensus half-life score per transcript
```

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
# CPU
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/exons.tsv:/data/exons.tsv \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-saluki-cpu:latest \
  saluki_predict.py -i /data/input.fa --exons /data/exons.tsv -o /out --data-head 0

# GPU
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/exons.tsv:/data/exons.tsv \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-saluki:latest \
  saluki_predict.py -i /data/input.fa --exons /data/exons.tsv -o /out --data-head 0
```

- `--data-head 0` = human, `--data-head 1` = mouse

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu \
  --saluki_input /path/to/input.fa --saluki_exons /path/to/exons.tsv --saluki_species human

# GPU
nextflow run main.nf -profile docker,gpu \
  --saluki_input /path/to/input.fa --saluki_exons /path/to/exons.tsv --saluki_species human
```

Only models with input provided will run; no ignore flags are needed.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--saluki_input` | none | FASTA, UTRs lowercase and CDS uppercase |
| `--saluki_exons` | none | TSV of exon lengths per transcript (`name`, `exon_lengths`); recommended |
| `--saluki_species` | `human` | Species: `human` or `mouse` |

## Example output

For one transcript, `predictions.tsv` holds the mean and standard deviation over the 50
members, for example a mean of -1.2 and a standard deviation of 0.3 for a short-lived mRNA.
Negative scores indicate less stable transcripts than average and positive scores more stable
ones.
