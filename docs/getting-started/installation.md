# Installation

## Requirements

- **Nextflow** >= 23.04.0 ([install guide](https://www.nextflow.io/docs/latest/getstarted.html))
- **Docker** or **Singularity** (for running model containers)
- **GPU** (optional) — needed only for seq2ribo; all other models work on CPU

## Install Nextflow

```bash
curl -s https://get.nextflow.io | bash
sudo mv nextflow /usr/local/bin/
```

Or via conda:

```bash
conda install -c bioconda nextflow
```

## Clone the pipeline

```bash
git clone https://github.com/ericmalekos/RNA-Zoo.git
cd RNA-Zoo
```

## Docker images

All model containers are hosted on GitHub Container Registry (`ghcr.io/ericmalekos/rnazoo-*`). Nextflow pulls them automatically on first run — no manual `docker pull` needed. The per-model image sizes are listed on the [home page](../index.md#whats-included) so you can pick a subset rather than pulling everything.

If you want to warm the cache up front, pick the loop that matches your hardware. Most users want the **CPU loop** unless they have a CUDA-capable GPU.

```bash
# --- CPU-only setup (~28 GB total compressed download)
# Selects the smaller -cpu variants where they exist. ernierna, rnaformer,
# and seq2ribo only ship a single image (built with CUDA-enabled framework
# but runs on CPU too) — included here for completeness.
for img in ribonn-cpu riboformer-cpu tristan-cpu saluki-cpu translationai-cpu \
           codontransformer-cpu rnafm-cpu rinalmo-cpu ernierna rnaformer \
           rhofold-cpu spotrna-cpu multirm-cpu utrlm-cpu; do
  docker pull ghcr.io/ericmalekos/rnazoo-${img}:latest
done
```

```bash
# --- GPU setup (~65 GB total compressed download)
# Pulls the CUDA-enabled variants for every tool. seq2ribo is GPU-only by
# design (mamba-ssm requires CUDA at import time).
for img in ribonn riboformer tristan seq2ribo saluki translationai \
           codontransformer rnafm rinalmo ernierna rnaformer rhofold \
           spotrna multirm utrlm; do
  docker pull ghcr.io/ericmalekos/rnazoo-${img}:latest
done
```

## Profiles

| Profile | Description |
|---------|-------------|
| `docker` | Use Docker as container engine |
| `singularity` | Use Singularity as container engine |
| `cpu` | Force CPU mode (GPU-only models auto-skip) |
| `gpu` | Enable GPU with NVIDIA runtime |
| `test` | Use bundled minimal test inputs |

Combine profiles with commas:

```bash
nextflow run . -profile docker,cpu,test
```

## Verify installation

```bash
# Run the test suite (13 models on CPU, ~5 minutes)
nextflow run . -profile test,docker,cpu
```

Expected output — all 13 models should pass:

```
RNAZOO:RIBONN (ribonn)                                | 1 of 1 ✔
RNAZOO:RIBOFORMER (riboformer:bacteria_cm_mg)         | 1 of 1 ✔
RNAZOO:RIBOTIE (ribotie)                              | 1 of 1 ✔
RNAZOO:TRANSLATIONAI (translationai)                  | 1 of 1 ✔
RNAZOO:SALUKI (saluki:human)                          | 1 of 1 ✔
RNAZOO:CODONTRANSFORMER (codontransformer:...)        | 1 of 1 ✔
RNAZOO:RNAFM (rnafm)                                  | 1 of 1 ✔
RNAZOO:RINALMO (rinalmo)                              | 1 of 1 ✔
RNAZOO:ERNIERNA (ernierna)                            | 1 of 1 ✔
RNAZOO:RNAFORMER (rnaformer)                          | 1 of 1 ✔
RNAZOO:SPOTRNA (spotrna)                              | 1 of 1 ✔
RNAZOO:MULTIRM (multirm)                              | 1 of 1 ✔
RNAZOO:UTRLM (utrlm:mrl)                              | 1 of 1 ✔
Succeeded   : 13
```

The test profile runs 13 of 15 models with bundled minimal inputs. Two models are excluded from the default CPU test:

| Model | Reason | Covered by `test_gpu`? |
|-------|--------|------------------------|
| seq2ribo | Requires GPU | Yes |
| RhoFold | Too slow on CPU (~5 min, 10 recycling iterations) | Yes |

> Riboformer uses the in-image E. coli dataset (`GSE119104_Mg_buffer`) via `--riboformer_bundled_dataset` — no external test data needed. See [the Riboformer page](../models/Riboformer.md) for how to point it at a bundled dataset.

### Run the GPU test suite

If you have an NVIDIA GPU available, run the extended test profile to also exercise seq2ribo and RhoFold:

```bash
# Run the GPU test suite (15 models, requires NVIDIA Container Toolkit)
nextflow run . -profile test_gpu,docker,gpu
```

Expected output — all 15 models should pass:

```
RNAZOO:RIBONN (ribonn)                                | 1 of 1 ✔
RNAZOO:RIBOFORMER (riboformer:bacteria_cm_mg)         | 1 of 1 ✔
RNAZOO:RIBOTIE (ribotie)                              | 1 of 1 ✔
RNAZOO:TRANSLATIONAI (translationai)                  | 1 of 1 ✔
RNAZOO:SALUKI (saluki:human)                          | 1 of 1 ✔
RNAZOO:CODONTRANSFORMER (codontransformer:...)        | 1 of 1 ✔
RNAZOO:RNAFM (rnafm)                                  | 1 of 1 ✔
RNAZOO:RINALMO (rinalmo)                              | 1 of 1 ✔
RNAZOO:ERNIERNA (ernierna)                            | 1 of 1 ✔
RNAZOO:RNAFORMER (rnaformer)                          | 1 of 1 ✔
RNAZOO:SPOTRNA (spotrna)                              | 1 of 1 ✔
RNAZOO:MULTIRM (multirm)                              | 1 of 1 ✔
RNAZOO:UTRLM (utrlm:mrl)                              | 1 of 1 ✔
RNAZOO:SEQ2RIBO (seq2ribo:te:hek293)                  | 1 of 1 ✔
RNAZOO:RHOFOLD (rhofold)                              | 1 of 1 ✔
Succeeded   : 15
```

This is identical to the CPU test profile but additionally provides
`--seq2ribo_input` and `--rhofold_input` so the two GPU-only / GPU-recommended models also run, and Riboformer's bundled-dataset test runs faster on GPU (~1.5 min vs ~2.5 min on CPU). Models with both CPU and GPU image variants automatically use their GPU images under `-profile gpu`.

### How profiles select container images

Most models ship two image variants on GHCR:

- `ghcr.io/ericmalekos/rnazoo-<tool>:latest` — CUDA-enabled GPU build (default)
- `ghcr.io/ericmalekos/rnazoo-<tool>-cpu:latest` — CPU-only build (smaller)

`-profile cpu` selects the `-cpu` image; `-profile gpu` selects the unsuffixed (GPU) image. Nextflow handles the pull automatically — you do not invoke Docker directly. Exception: seq2ribo ships only as a single GPU image (mamba-ssm requires CUDA at import time and auto-skips under `-profile cpu`).

**VRAM caveat:** running 14 models in parallel on a single GPU needs more memory than a typical consumer card (a 4 GB device will OOM partway through). If you have a small GPU, run models one-at-a-time with explicit `--<model>_input` flags instead of using the test profile.
