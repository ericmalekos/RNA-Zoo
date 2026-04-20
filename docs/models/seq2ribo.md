# seq2ribo

Predict ribosome profiling signals, translation efficiency, or protein expression from mRNA sequence.

- **Paper:** [bioRxiv 2026](https://www.biorxiv.org/content/10.64898/2026.02.08.700508v1)
- **Upstream:** https://github.com/Kingsford-Group/seq2ribo
- **License:** CMU Academic/Non-Commercial Research Use Only (commercial use prohibited)
- **Device:** GPU only (CUDA required, auto-skipped under `--profile cpu`)

## What it does

seq2ribo uses a Mamba state-space model to predict ribosome profiling data from mRNA sequence alone. It supports three prediction tasks:

- **`riboseq`**: per-position ribosome density profile
- **`te`**: translation efficiency (scalar per transcript)
- **`protein`**: protein expression level (scalar per transcript)

Models are available for 4 human cell lines: HEK293, LCL, RPE, iPSC.

## Input format

FASTA file of mRNA coding sequences (CDS only, or with UTRs if using `--use_utr`).

Example (`tests/data/seq2ribo_test.fa`):

```
>test_cds_1
AUGGCCAAAGCUACCUUGAAGCGAGCACUGGAGAGCUUUGCCAAGGCCUUGAAAGAGAUG
AAAGCCACCAAAGAAUGGAAUGCCGUGACCAAAGCUGCCAGCAUCCUGAAAGAGAAAGCCC
UGGAUUAG
```

## Output format

JSON file with per-sequence predictions:

```json
[
  {
    "id": "test_cds_1",
    "prediction": 2.2616412272516313
  }
]
```

For the `riboseq` task, `prediction` is an array of per-position values instead of a scalar.

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
docker run --rm \
  --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-seq2ribo:latest \
  /opt/conda/envs/seq2ribo/bin/python /opt/seq2ribo/scripts/run_inference.py \
    --task te \
    --cell-line hek293 \
    --fasta /data/input.fa \
    --output /out/seq2ribo_output.json
```

Note: on systems with snap-installed Docker, use `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all` instead of `--gpus all`.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,gpu \
  --seq2ribo_input /path/to/input.fa \
  --seq2ribo_task te \
  --seq2ribo_cell_line hek293
```

Only models with input provided will run — no ignore flags needed.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--seq2ribo_task` | `te` | Prediction task: `riboseq`, `te`, or `protein` |
| `--seq2ribo_cell_line` | `hek293` | Cell line: `hek293`, `lcl`, `rpe`, or `ipsc` |
| `--seq2ribo_use_utr` | `false` | Include UTR regions in prediction |

## Example output

```json
[
  {
    "id": "test_cds_1",
    "prediction": 2.2616412272516313
  }
]
```

A TE value of ~2.26 indicates the transcript is predicted to be translated at about 2^2.26 = ~4.8x the average efficiency in HEK293 cells.
