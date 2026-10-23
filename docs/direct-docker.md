# Run containers directly (no Nextflow)

Each image holds a model, its weights and a command-line entry point, so a single `docker run`
is enough for a quick test or a bug report. For larger runs, Nextflow adds parallel tasks,
resuming and file staging; see the [Quick Start](getting-started/quickstart.md).

## Common recipe

```bash
mkdir -p /path/to/output    # otherwise Docker creates it, owned by root
docker run --rm \
    -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
    -v /path/to/input.fa:/data/input.fa \
    -v /path/to/output:/out \
    ghcr.io/ericmalekos/rnazoo-rnafm-cpu:latest \
    rnafm_predict.py -i /data/input.fa -o /out
```

For another model, change the image and the command ([table below](#per-model-commands)). For a
GPU, drop `-cpu` from the image name and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`,
or `--gpus all`; both need the NVIDIA Container Toolkit.

## Things to know

- **User.** `-u $(id -u):$(id -g)` makes the output files yours instead of root's. It needs
  `-e HOME=/tmp -e USER=$(whoami)` too: PyTorch can fail at import when your user ID has no entry
  in the container's `/etc/passwd`.
- **Threads.** The pipeline caps each task's threads at `--task_cpus` with environment variables
  such as `OMP_NUM_THREADS` (the full list is in `nextflow.config`). A bare `docker run` sets
  none, so PyTorch, TensorFlow and BLAS may start a thread per core; add, for example,
  `-e OMP_NUM_THREADS=4` on a shared machine.
- **Log output.** If the log appears only at the end when piped or redirected, add
  `-e PYTHONUNBUFFERED=1`.

## Per-model commands

These commands use the mounts of the common recipe. Image names leave out the prefix
`ghcr.io/ericmalekos/rnazoo-` and the tag `:latest`. The embedding models also take
`--per-token`.

| Model | CPU image | GPU image | Command |
|-------|-----------|-----------|---------|
| [RNA-FM](models/RNAFM.md) | `rnafm-cpu` | `rnafm` | `rnafm_predict.py -i /data/input.fa -o /out` |
| [RiNALMo](models/RiNALMo.md) | `rinalmo-cpu` | `rinalmo` | `rinalmo_predict.py -i /data/input.fa -o /out` |
| [ERNIE-RNA](models/ERNIERNA.md) | `ernierna` | `ernierna` | `ernierna_predict.py -i /data/input.fa -o /out` |
| [Orthrus](models/Orthrus.md) | none | `orthrus` | `orthrus_predict.py -i /data/input.fa -o /out` |
| [HydraRNA](models/HydraRNA.md) | none | `hydrarna` | `hydrarna_predict.py -i /data/input.fa -o /out` |
| [RNAErnie](models/RNAErnie.md) | `rnaernie-cpu` | `rnaernie` | `rnaernie_predict.py -i /data/input.fa -o /out` |
| [PlantRNA-FM](models/PlantRNAFM.md) | `plantrnafm-cpu` | `plantrnafm` | `plantrnafm_predict.py -i /data/input.fa -o /out` |
| [CaLM](models/CaLM.md) | `calm-cpu` | `calm` | `calm_predict.py -i /data/input.fa -o /out` |
| [mRNABERT](models/mRNABERT.md) | `mrnabert-cpu` | `mrnabert` | `mrnabert_predict.py -i /data/input.fa -o /out` |
| [SpliceBERT](models/SpliceBERT.md) | `splicebert-cpu` | `splicebert` | `splicebert_predict.py -i /data/input.fa -o /out` |
| [RhoFold](models/RhoFold.md) | `rhofold-cpu` | `rhofold` | `rhofold_predict.py -i /data/input.fa -o /out` |
| [SPOT-RNA](models/SPOTRNA.md) | `spotrna-cpu` | `spotrna` | `spotrna_predict.py -i /data/input.fa -o /out --cpu 4`; on the GPU image, `--gpu 0` instead of `--cpu 4` |
| [DRfold2](models/DRfold2.md) | none | `drfold2` | `drfold2_predict.py -i /data/input.fa -o /out` |
| [MultiRM](models/MultiRM.md) | `multirm-cpu` | `multirm` | `multirm_predict.py -i /data/input.fa -o /out` |
| [UTR-LM](models/UTRLM.md) | `utrlm-cpu` | `utrlm` | `utrlm_predict.py -i /data/input.fa -o /out --task mrl --model-dir /opt/utrlm/Model` |
| [CodonTransformer](models/CodonTransformer.md) | `codontransformer-cpu` | `codontransformer` | `codon_transformer_predict.py -i /data/input.fa -o /out/optimized_codons.fa --organism "Homo sapiens"` |
| [Saluki](models/Saluki.md) | `saluki-cpu` | `saluki` | `saluki_predict.py -i /data/input.fa -o /out`; to set the splice track, mount an exon-length TSV and add `--exons /data/exons.tsv` |
| [TranslationAI](models/TranslationAI.md) | `translationai-cpu` | none (the tool hides the GPU) | `bash -c "cp /data/input.fa /tmp/input.fa && translationai -I /tmp/input.fa -t 0.5,0.5 && cp /tmp/input_pred*.txt /out/"` |

Orthrus, HydraRNA and DRfold2 have no CPU image; run them with the GPU options.

### Models with other inputs

**RiboNN** reads a TSV and must run from `/app`:

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
    -v /path/to/input.tsv:/data/input.tsv \
    -v /path/to/output:/out \
    ghcr.io/ericmalekos/rnazoo-ribonn-cpu:latest \
    bash -c "cd /app && python3 /opt/bin/ribonn_predict.py -i /data/input.tsv -o /out --species human"
```

**SpliceAI** and **Pangolin** read several files. Put them in one directory, mounted as `/work`:

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
    -v /path/to/inputs:/work \
    ghcr.io/ericmalekos/rnazoo-spliceai-cpu:latest \
    spliceai_predict.py -i /work/variants.vcf -o /work/variants.spliceai.vcf \
        -r /work/genome.fa -a grch38
```

For Pangolin, use the image `rnazoo-pangolin-cpu` and the command
`pangolin_predict.py -i /work/variants.vcf -r /work/genome.fa -a /work/annotation.db -o /work/variants.pangolin`.
[Its page](models/Pangolin.md) shows how to build `annotation.db` from a GTF.

**RiboTIE** runs in a directory that holds `config.yml` and the input files
([config layout](models/RiboTIE.md)). On the GPU image `rnazoo-tristan`, pass `--accelerator gpu`.

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
    -v "$PWD":/work -w /work \
    ghcr.io/ericmalekos/rnazoo-tristan-cpu:latest \
    bash -c "mkdir -p ribotie_out/dbs ribotie_out/out && ribotie config.yml --accelerator cpu --overwrite_data"
```

**Riboformer** reads a dataset directory mounted under `/opt/Riboformer/datasets/` and writes
its outputs, `model_prediction.txt` among them, into that directory. With a copy of the test data
from the repository:

```bash
cp -r tests/data/riboformer my_data
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
    -v "$PWD/my_data":/opt/Riboformer/datasets/my_data \
    ghcr.io/ericmalekos/rnazoo-riboformer-cpu:latest \
    bash -c "python data_processing.py -d my_data -r GSM3358138_filter_Cm_ctrl -t GSM3358140_freeze_Mg_ctrl && python transfer.py -i my_data -m bacteria_cm_mg"
```

## Help and debugging

Each RNA-Zoo wrapper lists its options with `--help`:

```bash
docker run --rm ghcr.io/ericmalekos/rnazoo-rnafm-cpu:latest rnafm_predict.py --help
```

To look around inside an image, start a shell:

```bash
docker run --rm -it -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
    ghcr.io/ericmalekos/rnazoo-rnafm-cpu:latest bash
```

The wrappers are in `/opt/bin` (ERNIE-RNA's in `/opt/ernie-rna`). Most upstream code is under
`/opt`; RiboNN's is under `/app`.
