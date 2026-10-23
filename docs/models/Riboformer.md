# Riboformer

Predict codon-level ribosome density in a target condition from a reference ribo-seq dataset and
the coding sequence.

- **Paper:** [Nature Communications 2024](https://www.nature.com/articles/s41467-024-46241-8)
- **Upstream:** https://github.com/lingxusb/Riboformer
- **License:** MIT (code and weights)
- **Device:** CPU or GPU (images `rnazoo-riboformer-cpu` and `rnazoo-riboformer`).

## What it does

Riboformer reads the reference density and the codons in a 40-codon window and predicts the
target-condition density at that codon. Upstream's `data_processing.py` builds the windows and
`transfer.py` applies one of five pretrained models:

| Model | Predicts |
|-------|----------|
| `yeast_disome` (default) | Yeast disome profiles |
| `bacteria_cm_mg` | E. coli profiles, high-Mg flash-frozen protocol |
| `yeast_aging` | Aged yeast (day 4) |
| `worm_aging` | Aged worm (day 12) |
| `covid_model` | SARS-CoV-2 (24 hpi) |

## Input

A directory with the WIGs `<reference>_f.wig`, `<reference>_r.wig`, `<target>_f.wig` and
`<target>_r.wig`, one genome ending in `.fasta` and one annotation ending in `.gff3`. WIG
headers must keep the layout of the bundled files, `fixedStep  chrom=<FASTA id>  start=1  step=1`
with two spaces between fields, as upstream reads the name by position. Only CDSs over 200 nt
in the top `--riboformer_threshold` percent by reference coverage are scored. The target WIGs
must exist, though prediction reads only the reference. Example: `tests/data/riboformer/`.

## Output

In `results/riboformer/`: `model_prediction.txt`, one predicted density per window and line, on
the log2 scale used in training; `pause_indices.txt`, copied through only if the input has one;
and, with `--riboformer_plot true`, `ribosome_density_plot.png`. The gene and codon of each
window (`zc.txt`) stay in the task work directory, under `datasets/nf_input/`.

Example (test profile, `bacteria_cm_mg`):

```
5.106406211853027344e+00
4.372481346130371094e+00
```

## Run with Docker

Mount the data directory into `datasets/`; the outputs, `zc.txt` included, are written into it.

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/data_dir:/opt/Riboformer/datasets/my_data \
  ghcr.io/ericmalekos/rnazoo-riboformer-cpu:latest \
  bash -c "python data_processing.py -d my_data -r ref_sample -t target_sample && python transfer.py -i my_data -m yeast_disome"
```

For the GPU image, use `rnazoo-riboformer:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --riboformer_input /path/to/data_dir \
  --riboformer_reference_wig ref_sample \
  --riboformer_target_wig target_sample
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/riboformer/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--riboformer_input` | `null` | Input directory |
| `--riboformer_reference_wig` | `null` | Reference WIG name, without `_f.wig` (required) |
| `--riboformer_target_wig` | `null` | Target WIG name (required) |
| `--riboformer_model` | `yeast_disome` | Pretrained model |
| `--riboformer_psite` | `14` | P-site offset (nt) |
| `--riboformer_wsize` | `40` | Window in codons; the models need 40 |
| `--riboformer_threshold` | `25` | Percent of genes kept, by reference coverage |
| `--riboformer_bundled_dataset` | `null` | Dataset in the image, instead of `--riboformer_input` |
| `--riboformer_plot` | `false` | Plot the predictions |

## Bundled datasets

Of upstream's datasets in `/opt/Riboformer/datasets/`, only `GSE119104_Mg_buffer` (E. coli) and
`GSE139036_disome` (yeast) have WIG, FASTA and GFF3 files. For the E. coli set:

```bash
nextflow run main.nf -profile docker,cpu \
  --riboformer_bundled_dataset GSE119104_Mg_buffer \
  --riboformer_reference_wig GSM3358138_filter_Cm_ctrl \
  --riboformer_target_wig GSM3358140_freeze_Mg_ctrl \
  --riboformer_model bacteria_cm_mg
```

## Limitations

- `transfer.py` predicts every `*xc.txt` in the dataset folder, and each bundled dataset already
  holds one, so bundled runs mix precomputed windows into the output. Keep no other `*xc.txt` in
  your own input.
- Preprocessing fails if too few genes pass the filters; use five or more, or lower
  `--riboformer_threshold`.
