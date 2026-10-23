# Installation

## Requirements

- [Nextflow](https://www.nextflow.io/docs/latest/install.html) 23.04.0 or later, which needs
  Java.
- Docker, or Singularity or Apptainer, to run the model images.
- For GPU runs, an NVIDIA GPU, and for Docker also the
  [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html):
  the `gpu` profile starts containers with `--runtime=nvidia`, which the toolkit provides. With
  Singularity, the `gpu` profile passes `--nv` instead.

Orthrus, HydraRNA and DRfold2 run only on a GPU. The other 20 models also run on the CPU.

## Install Nextflow

```bash
curl -s https://get.nextflow.io | bash
sudo mv nextflow /usr/local/bin/
```

Or with conda:

```bash
conda install -c bioconda nextflow
```

## Get the pipeline

```bash
git clone https://github.com/ericmalekos/RNA-Zoo.git
cd RNA-Zoo
```

## Container images

The images are on GitHub Container Registry as `ghcr.io/ericmalekos/rnazoo-<name>`. Nextflow
pulls the images of the models you run when it first needs them, so pulling ahead is optional.
With Singularity, Nextflow converts each image on first use; set `NXF_SINGULARITY_CACHEDIR` to a
directory with space to keep the converted images for later runs.

The `gpu` profile uses the CUDA images, `rnazoo-<name>`; the `cpu` profile uses the smaller
`rnazoo-<name>-cpu`. The exceptions:

- ERNIE-RNA has one image, `rnazoo-ernierna`, for both profiles.
- Orthrus, HydraRNA and DRfold2 have only a GPU image and are skipped under `cpu`.
- TranslationAI runs `rnazoo-translationai-cpu` under both profiles, because its command-line
  tool hides the GPU.
- Fine-tuning on saved embeddings runs in the CPU-only `rnazoo-finetune-head`.

The 23 images of the `gpu` profile add up to about 98 GB compressed, the 20 of the `cpu` profile
to about 32 GB; layers that images share are downloaded once. To pull a whole set ahead of time:

```bash
# Images of the gpu profile
for img in ribonn riboformer tristan translationai-cpu saluki codontransformer \
           rnafm rinalmo ernierna orthrus hydrarna rnaernie plantrnafm calm mrnabert \
           rhofold spotrna drfold2 multirm pangolin spliceai splicebert utrlm; do
  docker pull ghcr.io/ericmalekos/rnazoo-${img}:latest
done
```

```bash
# Images of the cpu profile
for img in ribonn-cpu riboformer-cpu tristan-cpu translationai-cpu saluki-cpu \
           codontransformer-cpu rnafm-cpu rinalmo-cpu ernierna rnaernie-cpu plantrnafm-cpu \
           calm-cpu mrnabert-cpu rhofold-cpu spotrna-cpu multirm-cpu pangolin-cpu \
           spliceai-cpu splicebert-cpu utrlm-cpu; do
  docker pull ghcr.io/ericmalekos/rnazoo-${img}:latest
done
```

To run the images without Nextflow, see [Direct Docker usage](../direct-docker.md).

## Profiles

Combine a container engine, a device and, optionally, a test profile, for example
`-profile test,docker,cpu`.

| Profile | Effect |
|---------|--------|
| `docker` | Run the images with Docker |
| `singularity` | Run the images with Singularity or Apptainer |
| `gpu` | GPU images, with the GPU passed to the containers |
| `cpu` | CPU images; GPU-only models are skipped with a warning |
| `test` | Test inputs from `tests/data/` for 19 models: all but Orthrus, HydraRNA, RhoFold and DRfold2 |
| `test_gpu` | `test` plus RhoFold and Orthrus |
| `test_singularity` | Test inputs for five models (RiboNN, RNA-FM, SpliceBERT, MultiRM, UTR-LM) |
| `test_finetune`, `test_finetune_from_emb`, `test_finetune_classify` | Fine-tuning tests; see [Fine Tuning](../finetuning.md#test-profiles) |

Always give `gpu` or `cpu`. With neither, the pipeline uses the GPU images but passes no GPU to
them.

## Check the installation

```bash
# With an NVIDIA GPU: 21 models
nextflow run main.nf -profile test_gpu,docker,gpu

# Without one: 19 models on the CPU images
nextflow run main.nf -profile test,docker,cpu

# With Singularity or Apptainer: five models
nextflow run main.nf -profile test_singularity,singularity,cpu
```

Every process should finish with a check mark, and the outputs land in `results_test/`.
RhoFold is left out of `test` because it is slow on the CPU. HydraRNA and DRfold2 are in no
test profile.
