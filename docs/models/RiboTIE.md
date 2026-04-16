# RiboTIE (TRISTAN)

Detect translated ORFs from ribo-seq + genomic sequence using a transformer model.

- **Paper:** [Nature Communications 2025](https://www.nature.com/articles/s41467-025-56543-0)
- **Upstream:** https://github.com/TRISTAN-ORF/TRISTAN (v1.1.1)
- **License:** Upstream repository license
- **Device:** CPU (slow) or GPU (recommended for real datasets)

## What it does

RiboTIE (implemented via the TRISTAN package) detects translated open reading frames (ORFs) by combining genomic sequence with ribo-seq data. It fine-tunes a pretrained transformer model on the user's ribo-seq data before predicting translated ORFs. The model outputs per-transcript translation initiation site (TIS) predictions as GTF annotations and CSV scores.

## Input format

A directory containing:

1. **Genome FASTA** (`.fa`): reference genome assembly
2. **GTF annotation** (`.gtf`): gene/transcript annotation
3. **BAM files** (`.bam`): transcriptome-mapped ribo-seq reads (one per sample)
4. **YAML config file**: specifying paths, sample mapping, and fold assignments

Example config (`config.yml`):

```yaml
fa_path: GRCh38v110_snippet.fa
gtf_path: GRCh38v110_snippet.gtf

ribo_paths:
  "sample1": SRR000001.bam
  "sample2": SRR000002.bam
  "sample3": SRR000003.bam

h5_path: ribotie_out/dbs/ribotie.h5
out_prefix: ribotie_out/out/ribotie

trained_model:
  folds:
    0:
      test: []
      train: ['sample2']
      transfer_checkpoint: /path/to/checkpoint_f0.ckpt
      val: ['sample3']
    1:
      test: ['sample3']
      train: ['sample1']
      transfer_checkpoint: /path/to/checkpoint_f1.ckpt
      val: ['sample2']
```

Note: sample IDs in `ribo_paths` must be strings (use quotes around numeric IDs).

## Output format

- **`*.gtf`**: predicted ORFs in GTF format
- **`*.csv`**: per-ORF prediction scores
- **`*.npy`** (optional): raw prediction arrays

## Run with Docker

```bash
docker run --rm \
  -v /path/to/data:/work \
  -w /work \
  ghcr.io/ericmalekos/rnazoo-tristan:latest \
  bash -c "mkdir -p ribotie_out/dbs ribotie_out/out && \
    ribotie config.yml --accelerator cpu --overwrite_data --max_epochs 10 --patience 3"
```

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --ribotie_input /path/to/data_dir \
  --ribotie_config /path/to/config.yml
```

Only models with input provided will run — no ignore flags needed.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--ribotie_max_epochs` | (upstream default) | Maximum training epochs |
| `--ribotie_patience` | (upstream default) | Early stopping patience |

## Bundled pretrained checkpoints

Located inside the Docker image at:

```
/opt/conda/envs/tristan/lib/python3.10/site-packages/transcript_transformer/pretrained/
  tt_models/Homo_sapiens.GRCh38.113_f{0..4}.tt.ckpt   # Human
  tt_models/Mus_musculus.GRCm39.112_f{0..4}.tt.ckpt    # Mouse
  rt_models/50perc_06_23_f{0,1}.rt.ckpt                # Pretrained RiboTIE
```

## Known issues

The bundled pretrained checkpoints (both `tt` and `rt` variants) have compatibility issues with TRISTAN v1.1.1 during the prediction step (`scalar_emb` / `use_seq`/`use_ribo` argument mismatch). Data processing (FASTA+GTF+BAM to HDF5) works correctly. This is an upstream issue; check the TRISTAN GitHub for updates.

## Pipeline steps

1. **Build HDF5 database** from FASTA + GTF + BAM (automatic)
2. **Fine-tune** the pretrained model on user's ribo-seq samples
3. **Predict** translated ORFs and emit per-sample GTF/CSV outputs
