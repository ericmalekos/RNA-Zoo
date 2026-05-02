# Run containers directly (no Nextflow)

Every RNAZoo image is self-contained: model weights are baked in, no runtime downloads are needed, and each ships a CLI wrapper you can invoke with a single `docker run`. Use this page if you don't want to set up Nextflow, or for quick one-offs and bug reports.

Nextflow is still recommended for large pipelines (parallelism, resume, staging) — see the [quickstart](getting-started/quickstart.md). The commands here are the raw equivalent.

## Common recipe

Every model follows the same invocation pattern:

```bash
docker run --rm \
    -u $(id -u):$(id -g) \
    -e HOME=/tmp -e USER=$(whoami) \
    -v /path/to/input.fa:/data/input.fa \
    -v /path/to/output:/out \
    ghcr.io/ericmalekos/rnazoo-<MODEL>-cpu:latest \
    <MODEL>_predict.py -i /data/input.fa -o /out
```

For a GPU-accelerated run, drop the `-cpu` suffix from the image tag and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`:

```bash
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
    -u $(id -u):$(id -g) \
    -e HOME=/tmp -e USER=$(whoami) \
    -v /path/to/input.fa:/data/input.fa \
    -v /path/to/output:/out \
    ghcr.io/ericmalekos/rnazoo-<MODEL>:latest \
    <MODEL>_predict.py -i /data/input.fa -o /out
```

See the [home-page table](index.md#whats-included) for inputs, outputs, and image sizes, and [installation](getting-started/installation.md) for pre-pulling a full set.

## Gotchas

A few things the Nextflow profile handles for you that you need to replicate with raw `docker run`:

- **UID / HOME / USER flags.** Without `-u $(id -u):$(id -g)` the container writes as root, leaving files you can't easily delete. Without `-e HOME=/tmp -e USER=$(whoami)` newer PyTorch versions crash at import when the host UID isn't in `/etc/passwd` (e.g. `KeyError: getpwuid(): uid not found`). Include both in every invocation.
- **Write permissions on the output mount.** The output directory on the host must exist and be writable by your UID (`mkdir -p /path/to/output` is usually enough).
- **GPU flag.** `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all` requires the NVIDIA Container Toolkit installed on the host. On Docker 19.03+ you can use `--gpus all` as an equivalent shortcut.
- **Line-buffered stdout.** If you pipe output through `tee` or redirect it and see nothing for a while, add `-e PYTHONUNBUFFERED=1` to force Python line-buffering.

## Per-model invocations

The single-input/single-output models (most of the zoo) all follow the same shape. Save yourself typing by exporting a helper:

```bash
run_rnazoo() {
    local model="$1"; shift
    docker run --rm \
        -u $(id -u):$(id -g) \
        -e HOME=/tmp -e USER=$(whoami) \
        -v "$PWD/input.fa:/data/input.fa" \
        -v "$PWD/out:/out" \
        "ghcr.io/ericmalekos/rnazoo-${model}-cpu:latest" \
        "$@"
}
```

Then: `run_rnazoo rnafm rnafm_predict.py -i /data/input.fa -o /out`, etc.

### Simple models (single-mount input → output dir)

| Model | In-container command |
|-------|----------------------|
| [RNA-FM](models/RNAFM.md) | `rnafm_predict.py -i /data/input.fa -o /out` |
| [RiNALMo](models/RiNALMo.md) | `rinalmo_predict.py -i /data/input.fa -o /out` |
| [UTR-LM](models/UTRLM.md) | `utrlm_predict.py -i /data/input.fa -o /out --task mrl --model-dir /opt/utrlm/Model` |
| [ERNIE-RNA](models/ERNIERNA.md) | `ernierna_predict.py -i /data/input.fa -o /out` |
| [RNAErnie](models/RNAErnie.md) | `rnaernie_predict.py -i /data/input.fa -o /out` |
| [PlantRNA-FM](models/PlantRNAFM.md) | `plantrnafm_predict.py -i /data/input.fa -o /out` |
| [RhoFold](models/RhoFold.md) | `rhofold_predict.py -i /data/input.fa -o /out` |
| [SPOT-RNA](models/SPOTRNA.md) | `spotrna_predict.py -i /data/input.fa -o /out` |
| [RNAformer](models/RNAformer.md) | `rnaformer_predict.py -i /data/input.fa -o /out` |
| [MultiRM](models/MultiRM.md) | `multirm_predict.py -i /data/input.fa -o /out` |
| [CodonTransformer](models/CodonTransformer.md) | `codon_transformer_predict.py -i /data/input.fa -o /out/optimized_codons.fa --organism "Homo sapiens"` |

### Models with model-family / cell-line flags

Same mount pattern as above, with an extra argument:

- **Saluki** (half-life): `bash -c "saluki_predict_fasta.py -d 0 -o /out /opt/saluki_models /data/input.fa"` — `-d 0` is human, `-d 1` is mouse.
- **RiboNN** (TE): the container expects its input staged into `/app/data/prediction_input1.txt`; easiest is `-v /path/to/input.txt:/app/data/prediction_input1.txt` and then `bash -c "cd /app && python3 /opt/bin/ribonn_predict.py -i /app/data/prediction_input1.txt -o /out --species human"`.
- **TranslationAI** (TIS/TTS/ORFs): `bash -c "translationai -i /data/input.fa -o /out"`.

### Multi-file inputs (ribo-seq)

These need a directory mount with several files + a config.

**RiboTIE** — needs FASTA + GTF + BAMs + YAML config in one directory. See [its page](models/RiboTIE.md) for the config layout. A bare-minimum invocation:

```bash
docker run --rm \
    -u $(id -u):$(id -g) \
    -e HOME=/tmp -e USER=$(whoami) \
    -v /path/to/data_dir:/work -w /work \
    ghcr.io/ericmalekos/rnazoo-tristan-cpu:latest \
    bash -c "mkdir -p ribotie_out/dbs ribotie_out/out && \
             ribotie config.yml --accelerator cpu --overwrite_data --max_epochs 10 --patience 3"
```

**Riboformer** — either give it your own data directory with WIG + FASTA + GFF3, or use one of the bundled in-image datasets:

```bash
# Bundled E. coli dataset (no external files needed)
docker run --rm \
    -u $(id -u):$(id -g) \
    -e HOME=/tmp -e USER=$(whoami) \
    -v $PWD/out:/out \
    ghcr.io/ericmalekos/rnazoo-riboformer-cpu:latest \
    bash -c "cd /opt/Riboformer/Riboformer && \
             python data_processing.py -d GSE119104_Mg_buffer \
                 -r GSM3358138_filter_Cm_ctrl -t GSM3358140_freeze_Mg_ctrl && \
             python transfer.py -i GSE119104_Mg_buffer -m bacteria_cm_mg && \
             cp /opt/Riboformer/datasets/GSE119104_Mg_buffer/model_prediction.txt /out/"
```

### GPU-only models

Both **seq2ribo** and **Orthrus** require CUDA at import time (mamba-ssm); they cannot run on CPU.

```bash
# seq2ribo (riboseq / TE / protein)
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
    -u $(id -u):$(id -g) \
    -e HOME=/tmp -e USER=$(whoami) \
    -v /path/to/input.fa:/data/input.fa \
    -v /path/to/output:/out \
    ghcr.io/ericmalekos/rnazoo-seq2ribo:latest \
    /opt/seq2ribo/scripts/run_inference.py -i /data/input.fa -o /out --task te --cell_line hek293

# Orthrus (mature-mRNA embeddings, 4-track 512-d)
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
    -u $(id -u):$(id -g) \
    -e HOME=/tmp -e USER=$(whoami) \
    -v /path/to/input.fa:/data/input.fa \
    -v /path/to/output:/out \
    ghcr.io/ericmalekos/rnazoo-orthrus:latest \
    orthrus_predict.py -i /data/input.fa -o /out
```

## Help text

Every CLI wrapper accepts `--help`:

```bash
docker run --rm ghcr.io/ericmalekos/rnazoo-rnafm-cpu:latest rnafm_predict.py --help
```

## Debugging inside a container

Drop into an interactive shell to poke around (useful for schema questions, tweaking model flags, checking bundled data paths):

```bash
docker run --rm -it \
    -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
    ghcr.io/ericmalekos/rnazoo-<model>-cpu:latest bash
```

Most images have the source code under `/app` or `/opt/<upstream>/` and the CLI wrapper under `/opt/bin/`.
