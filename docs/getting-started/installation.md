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

All model containers are hosted on GitHub Container Registry (`ghcr.io/ericmalekos/rnazoo-*`). Nextflow pulls them automatically on first run — no manual `docker pull` needed.

To pre-pull all images:

```bash
for img in ribonn-cpu riboformer tristan seq2ribo saluki translationai \
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
# Run the test suite (11 models on CPU, ~2 minutes)
nextflow run . -profile test,docker,cpu
```

Expected output — all 11 models should pass:

```
RNAZOO:RIBONN (ribonn)                         | 1 of 1 ✔
RNAZOO:TRANSLATIONAI (translationai)            | 1 of 1 ✔
RNAZOO:SALUKI (saluki:human)                    | 1 of 1 ✔
RNAZOO:CODONTRANSFORMER (codontransformer:...)  | 1 of 1 ✔
RNAZOO:RNAFM (rnafm)                           | 1 of 1 ✔
RNAZOO:RINALMO (rinalmo)                       | 1 of 1 ✔
RNAZOO:ERNIERNA (ernierna)                     | 1 of 1 ✔
RNAZOO:RNAFORMER (rnaformer)                   | 1 of 1 ✔
RNAZOO:SPOTRNA (spotrna)                       | 1 of 1 ✔
RNAZOO:MULTIRM (multirm)                       | 1 of 1 ✔
RNAZOO:UTRLM (utrlm:mrl)                       | 1 of 1 ✔
Succeeded   : 11
```

The test profile runs 11 of 15 models with bundled minimal inputs. Four models are excluded from the default test:

| Model | Reason |
|-------|--------|
| Riboformer | Test dataset too large to bundle (240 MB) |
| RiboTIE | Upstream checkpoint compatibility issue |
| seq2ribo | Requires GPU |
| RhoFold | Too slow on CPU (~5 min, 10 recycling iterations) |
