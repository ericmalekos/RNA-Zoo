# Installation

## Requirements

- **Nextflow** >= 23.04.0 ([install guide](https://www.nextflow.io/docs/latest/getstarted.html))
- **Docker** or **Singularity** (for running model containers)
- **NVIDIA GPU** (recommended) — required for seq2ribo and Orthrus; foundation/structure models also run much faster on GPU. CPU works for the other 13 models, just slower.
- **NVIDIA Container Toolkit** (for GPU runs) — needed so Docker can expose the GPU to containers. See the [official install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html). Without it, GPU profiles fail with `unknown runtime: nvidia`.

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

If you'd rather skip Nextflow entirely and drive the containers yourself, see the [Direct Docker guide](../direct-docker.md) for per-model `docker run` recipes.

If you want to warm the cache up front, pick the loop that matches your hardware. **If you have an NVIDIA GPU, use the GPU loop below — that's the project's default and the path the test suite is tuned for.** The CPU loop is the fallback for hardware without CUDA.

```bash
# --- GPU setup (~70 GB total compressed download)
# Pulls the CUDA-enabled variants for every tool. seq2ribo and orthrus
# are GPU-only by design (mamba-ssm requires CUDA at import time).
for img in ribonn riboformer tristan seq2ribo saluki translationai \
           codontransformer rnafm rinalmo ernierna orthrus rnaformer \
           rhofold spotrna multirm utrlm; do
  docker pull ghcr.io/ericmalekos/rnazoo-${img}:latest
done
```

> **VRAM caveat:** running 15+ models in parallel on a single GPU needs
> more memory than a typical consumer card (a 4 GB device will OOM
> partway through). If you have a small GPU, run models one-at-a-time
> with explicit `--<model>_input` flags instead of using the test profile.

```bash
# --- CPU-only setup (~28 GB total compressed download)
# Selects the smaller -cpu variants where they exist. ernierna and
# rnaformer only ship a single image (built with CUDA-enabled framework
# but runs on CPU too) — included here for completeness. seq2ribo and
# orthrus are GPU-only and not in this list.
for img in ribonn-cpu riboformer-cpu tristan-cpu saluki-cpu translationai-cpu \
           codontransformer-cpu rnafm-cpu rinalmo-cpu ernierna rnaformer \
           rhofold-cpu spotrna-cpu multirm-cpu utrlm-cpu; do
  docker pull ghcr.io/ericmalekos/rnazoo-${img}:latest
done
```

> **CPU performance note:** foundation models (RNA-FM, RiNALMo,
> ERNIE-RNA, UTR-LM) take ~30–60 s per inference call on CPU and
> sub-second on GPU. Use the GPU loop above if you have an NVIDIA card.

## Profiles

| Profile | Description |
|---------|-------------|
| `docker` | Use Docker as container engine |
| `singularity` | Use Singularity as container engine |
| `gpu` | Enable GPU with NVIDIA runtime (default for the test suite) |
| `cpu` | Force CPU mode (GPU-only models auto-skip with a warning) |
| `test` | Use bundled minimal test inputs (CPU-friendly subset) |
| `test_gpu` | Use bundled minimal test inputs including GPU-only / GPU-recommended models (seq2ribo, RhoFold, Orthrus) |

Combine profiles with commas:

```bash
nextflow run . -profile test_gpu,docker,gpu
```

## Verify installation

If you have an NVIDIA GPU, run the GPU test suite — this is the canonical end-to-end check:

```bash
# Run the GPU test suite (16 models, requires NVIDIA Container Toolkit)
nextflow run . -profile test_gpu,docker,gpu
```

Expected output — all 16 models should pass:

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
RNAZOO:ORTHRUS (orthrus)                              | 1 of 1 ✔
RNAZOO:RNAFORMER (rnaformer)                          | 1 of 1 ✔
RNAZOO:SPOTRNA (spotrna)                              | 1 of 1 ✔
RNAZOO:MULTIRM (multirm)                              | 1 of 1 ✔
RNAZOO:UTRLM (utrlm:mrl)                              | 1 of 1 ✔
RNAZOO:SEQ2RIBO (seq2ribo:te:hek293)                  | 1 of 1 ✔
RNAZOO:RHOFOLD (rhofold)                              | 1 of 1 ✔
Succeeded   : 16
```

Riboformer's bundled-dataset test runs faster on GPU (~1.5 min vs ~2.5 min on CPU). Models with both CPU and GPU image variants automatically use their GPU images under `-profile gpu`.

### CPU fallback

If you don't have an NVIDIA GPU, the smaller `test` profile runs the 13 of 16 models that work on CPU in a reasonable time:

```bash
# Run the CPU test suite (13 models on CPU, ~5 minutes)
nextflow run . -profile test,docker,cpu
```

Expected output — all 13 should pass:

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

Three of the 16 models are excluded from the default CPU test:

| Model | Reason | Covered by `test_gpu`? |
|-------|--------|------------------------|
| seq2ribo | GPU-only (mamba-ssm requires CUDA at import) | Yes |
| Orthrus | GPU-only (mamba-ssm requires CUDA at import) | Yes |
| RhoFold | Too slow on CPU (~5 min, 10 recycling iterations) | Yes |

> Riboformer uses the in-image E. coli dataset (`GSE119104_Mg_buffer`) via `--riboformer_bundled_dataset` — no external test data needed. See [the Riboformer page](../models/Riboformer.md) for how to point it at a bundled dataset.

### How profiles select container images

Most models ship two image variants on GHCR:

- `ghcr.io/ericmalekos/rnazoo-<tool>:latest` — CUDA-enabled GPU build (default)
- `ghcr.io/ericmalekos/rnazoo-<tool>-cpu:latest` — CPU-only build (smaller)

`-profile gpu` selects the unsuffixed (GPU) image; `-profile cpu` selects the `-cpu` image. Nextflow handles the pull automatically — you do not invoke Docker directly. Exceptions: seq2ribo and Orthrus ship only as a single GPU image (mamba-ssm requires CUDA at import time and they auto-skip under `-profile cpu`).
