# UTR-LM

Predict 5'UTR expression metrics: mean ribosome loading, translation efficiency, or expression level.

- **Paper:** [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00823-9)
- **Upstream:** https://github.com/a96123155/UTR-LM
- **License:** GPL-3.0
- **Device:** CPU or GPU (very lightweight ~5M parameter model)

## What it does

UTR-LM is a 5'UTR language model pretrained on RNA sequences from 5 species using masked language modeling with secondary structure and minimum free energy supervision. It predicts expression-related metrics from 5'UTR sequences:

- **MRL** (Mean Ribosome Loading): from synthetic 50-nt UTR library (Sample et al.)
- **TE** (Translation Efficiency): log-transformed, cell-line specific
- **EL** (Expression Level): log-transformed RNA-seq expression, cell-line specific

## Input format

FASTA file of 5'UTR DNA sequences (A, C, G, T alphabet; U is auto-converted to T):

```
>synthetic_utr_1
AATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAA
>synthetic_utr_2
GCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC
```

- **MRL task**: uses 50-nt sequences (last 50 nt if longer)
- **TE/EL tasks**: uses last 100 nt of the 5'UTR

Shorter sequences are automatically padded.

## Output format

**`predictions.tsv`** — one prediction per sequence:

```
header	sequence	mean_ribosome_loading
synthetic_utr_1	AATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAA	8.053340
synthetic_utr_2	GCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC	5.337085
synthetic_utr_3	TGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATG	6.575327
```

## Run with Docker

```bash
# MRL prediction (default)
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-utrlm:latest \
  utrlm_predict.py -i /data/input.fa -o /out --task mrl --model-dir /opt/utrlm/Model

# TE prediction for HEK cells
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-utrlm:latest \
  utrlm_predict.py -i /data/input.fa -o /out --task te --cell-line HEK --model-dir /opt/utrlm/Model
```

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --utrlm_input /path/to/input.fa \
  --utrlm_task mrl
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/utrlm/utrlm_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--utrlm_task` | `mrl` | Prediction task: `mrl`, `te`, or `el` |
| `--utrlm_cell_line` | `HEK` | Cell line for TE/EL tasks: `HEK`, `pc3`, or `Muscle` |

## Available tasks

| Task | Label | Input Length | Cell Lines | Description |
|------|-------|-------------|------------|-------------|
| `mrl` | Mean Ribosome Loading | 50 nt | N/A | From synthetic UTR library |
| `te` | Translation Efficiency (log) | 100 nt | HEK, pc3, Muscle | Cell-line specific |
| `el` | Expression Level (log) | 100 nt | HEK, pc3, Muscle | RNA-seq based |

## Technical notes

- Uses a custom fork of Facebook's ESM library with RNA-specific alphabet and secondary structure heads.
- Architecture: 6-layer ESM2 transformer (128-d, 16 heads) + linear classification head.
- Weights are bundled in the upstream repo (~1.1 GB total for all tasks/folds).
- MRL has 1 fold; TE/EL have 10 folds each (use `--folds all` for ensemble averaging).
- The model uses the CLS/BOS token embedding for per-sequence prediction.
