# Riboformer

Predict and refine codon-level ribosome densities from ribo-seq data.

- **Paper:** [Nature Communications 2024](https://www.nature.com/articles/s41467-024-46241-8)
- **Upstream:** https://github.com/lingxusb/Riboformer
- **License:** Upstream repository license
- **Device:** CPU or GPU. Two image variants:
    - `rnazoo-riboformer:latest` — CUDA-enabled (default, used with `-profile gpu`)
    - `rnazoo-riboformer-cpu:latest` — CPU-only (smaller, used with `-profile cpu`)

## What it does

Riboformer is a transformer model that takes existing ribo-seq data (ribosome profiling WIG coverage) along with genome sequence and annotation, and predicts refined codon-level ribosome densities. It can transfer learned patterns from a reference condition to a target condition.

Pre-trained models are available for: yeast (mono/disome), E. coli, C. elegans, and SARS-CoV-2.

## Input format

A directory containing:

1. **WIG files** (forward + reverse strands): ribosome profiling coverage for reference and target conditions
   - `<reference>_f.wig`, `<reference>_r.wig`
   - `<target>_f.wig`, `<target>_r.wig`
2. **FASTA file**: genome sequence
3. **GFF3 file**: gene annotation

The bundled datasets are in `/opt/Riboformer/datasets/` inside the Docker image (e.g., `GSE152850_yeast/`).

## Output format

- **`model_prediction.txt`**: codon-level predicted ribosome density values (one value per line per codon)
- **`pause_indices.txt`** (optional): ribosome pause indices per codon

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

Using the bundled yeast disome dataset (CPU shown; for GPU swap `rnazoo-riboformer-cpu` → `rnazoo-riboformer` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`):

```bash
docker run --rm \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-riboformer-cpu:latest \
  bash -c "cd /opt/Riboformer/Riboformer && \
    python transfer.py -i GSE152850_yeast -m yeast_disome && \
    cp /opt/Riboformer/datasets/GSE152850_yeast/model_prediction.txt /out/"
```

With your own data (two-step pipeline):

```bash
docker run --rm \
  -v /path/to/your/data:/opt/Riboformer/datasets/my_data \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-riboformer:latest \
  bash -c "cd /opt/Riboformer/Riboformer && \
    python data_processing.py -d my_data -r reference_wig_name -t target_wig_name -p 14 -w 40 -th 25 && \
    python transfer.py -i my_data -m yeast_disome && \
    cp /opt/Riboformer/datasets/my_data/model_prediction.txt /out/"
```

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu \
  --riboformer_input /path/to/data_dir \
  --riboformer_reference_wig reference_name \
  --riboformer_target_wig target_name \
  --riboformer_model yeast_disome

# GPU
nextflow run main.nf -profile docker,gpu \
  --riboformer_input /path/to/data_dir \
  --riboformer_reference_wig reference_name \
  --riboformer_target_wig target_name \
  --riboformer_model yeast_disome
```

Only models with input provided will run — no ignore flags needed.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--riboformer_model` | `yeast_disome` | Pre-trained model to use |
| `--riboformer_psite` | `14` | P-site offset |
| `--riboformer_wsize` | `40` | Window size |
| `--riboformer_threshold` | `25` | Minimum read threshold |
| `--riboformer_bundled_dataset` | `null` | Use a dataset already inside the image (skips external staging). When set, `--riboformer_input` is ignored. See "Bundled datasets" below. |

### Bundled datasets

The Docker image ships with several upstream datasets at `/opt/Riboformer/datasets/`. Pointing `--riboformer_bundled_dataset` at one of these lets you run end-to-end without supplying external files:

```bash
nextflow run main.nf -profile docker,cpu \
  --riboformer_bundled_dataset GSE119104_Mg_buffer \
  --riboformer_reference_wig GSM3358138_filter_Cm_ctrl \
  --riboformer_target_wig GSM3358140_freeze_Mg_ctrl \
  --riboformer_model bacteria_cm_mg
```

Datasets that have all the files needed for end-to-end inference (WIG + FASTA + GFF):

| Bundled dataset | Organism | Reference / target WIG names | Suggested model |
|-----------------|----------|-------------------------------|-----------------|
| `GSE119104_Mg_buffer` | E. coli (~146 MB) | `GSM3358138_filter_Cm_ctrl` / `GSM3358140_freeze_Mg_ctrl` | `bacteria_cm_mg` |
| `GSE139036_disome` | Yeast disome (~244 MB) | `GSM4127880_end3SM015Fd` / `GSM4127896_SM015M` | `yeast_disome` |

The default `-profile test` uses the **external-input** path against a ~2 MB subsample of `GSE119104_Mg_buffer` committed to `tests/data/riboformer/` (generated with `scripts/subsample_mg_buffer.py` — first 100 kb of NC_000913.2 + matching WIG slices). The bundled-mode path is exercised by the recipes above but not by CI.

## Available pre-trained models

| Dataset | Description |
|---------|-------------|
| `GSE152850_yeast` | Yeast monosome/disome |
| `GSE139036_disome` | Disome profiling |
| `GSE152850_celegans` | C. elegans |
| `GSE119104_Mg_buffer` | E. coli |
| `GSE165592_trmD` | E. coli trmD |
| `GSE77617_miniORF` | Mini-ORF |
| `GSE152664_circuit` | Synthetic circuit |

## Example output

```
1.629764437675476074e+00
1.895173668861389160e+00
2.439188957214355469e+00
4.431646347045898438e+00
5.384204864501953125e+00
```

Each line is the predicted ribosome density for one codon position.
