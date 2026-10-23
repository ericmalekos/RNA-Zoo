# SPOT-RNA

Predict RNA secondary structure, including pseudoknots and non-canonical base pairs.

- **Paper:** [Nature Communications 2019](https://doi.org/10.1038/s41467-019-13395-9)
- **Upstream:** https://github.com/jaswindersingh2/SPOT-RNA
- **License:** MPL-2.0 (code). The model archive is hosted outside the repository and states no
  terms of its own; the README names MPL-2.0 for the project without saying whether it covers
  the archive, so commercial use and redistribution of the weights are unclear.
- **Device:** CPU or GPU (images `rnazoo-spotrna-cpu` and `rnazoo-spotrna`).

## What it does

SPOT-RNA is an ensemble of five networks (2D ResNet blocks, a 2D BiLSTM and a fully connected
block; 17.5 million parameters in all), trained on 10,814 bpRNA structures and then on 120
high-resolution structures by transfer learning. It averages the five base-pair probability maps
and calls pairs at 0.335 or more, keeping only the most probable partner of each base.

## Input

FASTA. Letters are uppercased and T becomes U. There is no length cap; upstream quotes about
16 GB of RAM for sequences under 500 nt.

Example (`tests/data/spotrna_test.fa`):

```
>2zzm_B
GGCAGAUCUGAGCCUGGGAGCUCUCUGCC
```

## Output

In `spotrna_out/`:

- `structures.txt`: header, sequence and dot-bracket line for each sequence; pseudoknots use
  `[]` and `{}`
- per sequence, named after the first word of its header (`/` and `:` become `_`): the pairs in
  `<name>.bpseq` and `<name>.ct`, and the L × L pair probabilities (upper triangle) in `<name>.prob`
- with plotting on: `<name>_contact.png`, a heatmap of `<name>.prob`

Example `structures.txt`, for the input above:

```
>2zzm_B
GGCAGAUCUGAGCCUGGGAGCUCUCUGCC
((((((...(((((...).))))))))))
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-spotrna-cpu:latest \
  spotrna_predict.py -i /data/input.fa -o /out --cpu 4
```

For the GPU image, use `rnazoo-spotrna:latest`, add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`
and replace `--cpu 4` with `--gpu 0` (the default, `--gpu -1`, runs on the CPU). Add `--plot`
for the heatmaps.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --spotrna_input /path/to/input.fa
```

Use `-profile docker,gpu` for the GPU image. On the CPU, SPOT-RNA uses `--task_cpus` threads
(default 4). Results go to `results/spotrna/spotrna_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--spotrna_input` | `null` | FASTA file |
| `--spotrna_plot` | `false` | Also write `<name>_contact.png` heatmaps |

## Limitations

- If any sequence yields no structure, the run fails after the others finish and names it.
- The dot-bracket line has three bracket levels; a pair that fits none appears only in the
  `.bpseq` and `.ct` files.
