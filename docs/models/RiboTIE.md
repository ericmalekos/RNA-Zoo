# RiboTIE (TRISTAN)

Detect translated ORFs from ribosome profiling reads with a transformer model.

- **Paper:** [Nature Communications 2025](https://www.nature.com/articles/s41467-025-56543-0)
- **Upstream:** https://github.com/TRISTAN-ORF/TRISTAN (v1.1.1)
- **License:** MIT (code and weights)
- **Device:** CPU or GPU (images `rnazoo-tristan-cpu` and `rnazoo-tristan`).

## What it does

RiboTIE scores every transcript position as a translation start from the ribosome profiling
reads, with a Performer transformer. Two human models, pretrained on eight datasets and split by
chromosome into complementary folds, are fine-tuned on each sample before predicting and listing
the called ORFs.

## Input

A directory with the genome FASTA, a GTF and, per sample, a BAM or SAM of reads mapped to the
transcriptome; plus a YAML config. The module copies the directory to `data/`, so config paths
start with `data/`, and sets `h5_path` and `out_prefix` itself. Transcripts over 30,000 nt are
skipped.

Example (`tests/data/ribotie_config.yml`, shortened):

```yaml
gtf_path : data/GRCh38v110_snippet.gtf
fa_path  : data/GRCh38v110_snippet.fa
h5_path  : ribotie_out/dbs/ribotie.h5
out_prefix : ribotie_out/out/ribotie
ribo_paths :
  SRR000001 : data/SRR000001.bam
  SRR000002 : data/SRR000002.bam
```

## Output

In `results/ribotie/ribotie_out/out/`, per sample: `ribotie_<sample>.csv` and `.gtf` with the
called ORFs (`.novel.*` for novel ORFs, `.redundant.*` before upstream's CDS variant filter),
`.npy` with raw scores for every position, and the fine-tuned models (`_f0.rt.ckpt`,
`_f1.rt.ckpt`, `_params.rt.yml`). `ribotie_out/dbs/ribotie.h5` holds the parsed inputs.

Example (`ribotie_SRR000001.csv` from the test profile, first columns):

```
ribotie_score,ribotie_rank,seqname,ORF_id,ORF_len,transcript_id,transcript_len,start_codon,stop_codon,strand,ORF_type,...
0.6596,1,1,ENST00000673477_121,1944,ENST00000673477,4098,ATG,TAG,+,annotated CDS,...
```

## Run with Docker

From a directory holding `config.yml` and the inputs in `data/`:

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v "$PWD":/work -w /work \
  ghcr.io/ericmalekos/rnazoo-tristan-cpu:latest \
  bash -c "mkdir -p ribotie_out/dbs ribotie_out/out && ribotie config.yml --accelerator cpu --overwrite_data"
```

For the GPU image, use `rnazoo-tristan:latest`, add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`
and pass `--accelerator gpu`.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --ribotie_input /path/to/data \
  --ribotie_config /path/to/config.yml
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/ribotie/ribotie_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--ribotie_input` | `null` | Directory with the FASTA, GTF and read files |
| `--ribotie_config` | `null` | YAML config (required with `--ribotie_input`) |
| `--ribotie_max_epochs` | `null` | Maximum fine-tuning epochs; unset keeps upstream's default |
| `--ribotie_patience` | `null` | Early-stopping patience; unset keeps upstream's default |
| `--ribotie_checkpoint` | `null` | Fine-tuned `.rt.ckpt` written into the config's `transfer_checkpoint` lines |

## Limitations

- `--ribotie_checkpoint` rewrites only `transfer_checkpoint` lines already in the config, all to
  one path and with a two-space indent; upstream's `trained_model` block nests that key deeper
  and gives each fold its own checkpoint. Check the rewritten `config.yml` in the work directory.
  The file is not staged, so it must be visible inside the container.
