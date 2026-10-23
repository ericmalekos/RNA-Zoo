# Quick Start

Run these commands in the cloned repository ([Installation](installation.md)). They use the CPU
images; with an NVIDIA GPU, write `gpu` instead of `cpu` in the profile. Orthrus, HydraRNA and
DRfold2 need a GPU and are skipped under `cpu`.

## Run one model

A model runs only when its input is set, so there is nothing to switch off.

```bash
# RNA embeddings (RNA-FM)
nextflow run main.nf -profile docker,cpu --rnafm_input my_rna.fa

# Translation efficiency (RiboNN): a TSV of 5' UTR, CDS and 3' UTR sequences
nextflow run main.nf -profile docker,cpu --ribonn_input my_transcripts.tsv

# RNA 3D structure (RhoFold)
nextflow run main.nf -profile docker,cpu --rhofold_input my_rna.fa

# RNA modifications (MultiRM)
nextflow run main.nf -profile docker,cpu --multirm_input my_rna.fa
```

Each model's page gives its input format and parameters.

## Run several models

Set several inputs and the models run in parallel:

```bash
nextflow run main.nf -profile docker,cpu \
  --rnafm_input sequences.fa \
  --spotrna_input sequences.fa \
  --multirm_input sequences.fa
```

## Output directory and CPUs

Each model writes to `<outdir>/<model>/`, with `results/` as the default `--outdir`;
`--<model>_outdir` moves one model's results. Each task gets `--task_cpus` CPUs (default 4), and
the thread limits inside the containers follow it.

```bash
nextflow run main.nf -profile docker,cpu \
  --rnafm_input sequences.fa \
  --outdir my_project/results \
  --task_cpus 8
```

The results are laid out by model:

```
results/
  ribonn/
    ribonn_out/
      prediction_output.txt
  rnafm/
    rnafm_out/
      sequence_embeddings.npy
      labels.txt
  spotrna/
    spotrna_out/
      structures.txt
  ...
```

## Parameters file

For many parameters, write them to a YAML file and pass it with `-params-file`.
`nextflow.config` lists every parameter with its default.

```yaml
outdir: my_results
rnafm_input: data/rna_sequences.fa
rnafm_per_token: true
multirm_input: data/rna_sequences.fa
multirm_alpha: 0.01
```

```bash
nextflow run main.nf -profile docker,cpu -params-file my_params.yml
```

## Fine-tuning

The nine foundation models can train a prediction head on your labeled sequences:

```bash
nextflow run main.nf -profile docker,cpu \
  --rnafm_finetune_input my_labels.tsv \
  --rnafm_finetune_label te
```

See [Fine Tuning](../finetuning.md). The fine-tuning modules of RiboNN and UTR-LM currently fail.

## Without Nextflow

Each image also runs with a plain `docker run`; see [Direct Docker usage](../direct-docker.md).
