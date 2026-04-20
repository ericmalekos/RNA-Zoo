# RiboTIE (TRISTAN)

Detect translated ORFs from ribo-seq + genomic sequence using a transformer model.

- **Paper:** [Nature Communications 2025](https://www.nature.com/articles/s41467-025-56543-0)
- **Upstream:** https://github.com/TRISTAN-ORF/TRISTAN (v1.1.1)
- **License:** Upstream repository license
- **Device:** CPU or GPU. Two image variants:
    - `rnazoo-tristan:latest` — CUDA-enabled (default, used with `-profile gpu`, recommended for real datasets)
    - `rnazoo-tristan-cpu:latest` — CPU-only (smaller, used with `-profile cpu`, viable for small datasets)

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

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
# CPU
docker run --rm \
  -v /path/to/data:/work \
  -w /work \
  ghcr.io/ericmalekos/rnazoo-tristan-cpu:latest \
  bash -c "mkdir -p ribotie_out/dbs ribotie_out/out && \
    ribotie config.yml --accelerator cpu --overwrite_data --max_epochs 10 --patience 3"

# GPU
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/data:/work \
  -w /work \
  ghcr.io/ericmalekos/rnazoo-tristan:latest \
  bash -c "mkdir -p ribotie_out/dbs ribotie_out/out && \
    ribotie config.yml --accelerator gpu --overwrite_data --max_epochs 10 --patience 3"
```

## Run with Nextflow

```bash
# CPU (slow but works for the bundled test data and small inputs)
nextflow run main.nf -profile docker,cpu \
  --ribotie_input /path/to/data_dir \
  --ribotie_config /path/to/config.yml

# GPU (recommended for real ribo-seq datasets)
nextflow run main.nf -profile docker,gpu \
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

The README-documented invocations (`tis_transformer config.yml --model human` and `ribotie config.yml`) work correctly with the bundled pretrained checkpoints — the standard pipeline used by this module is unaffected.

A latent upstream bug exists in `transcript_transformer.predict()` (v1.1.1) that surfaces only in non-default configurations: when a user provides a hand-written `trained_model:` block in the YAML pointing at a bundled `tt`/`rt` checkpoint, `predict()` reloads the checkpoint without passing `use_seq`/`use_ribo`, triggering an `AttributeError` (`tt`) or `TypeError` (`rt`). The default `ribotie config.yml` flow avoids this because it goes through `train()` first, which loads the checkpoint correctly. See `docs/tristan_issue/GITHUB_ISSUE.md` for full details.

## Pipeline steps

1. **Build HDF5 database** from FASTA + GTF + BAM (automatic)
2. **Fine-tune** the pretrained model on user's ribo-seq samples
3. **Predict** translated ORFs and emit per-sample GTF/CSV outputs
