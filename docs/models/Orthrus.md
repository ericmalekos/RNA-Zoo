# Orthrus

Mamba-based mature mRNA foundation model. Produces 256-d or 512-d global embeddings from full mRNA sequences for downstream property prediction (half-life, ribosome load, localization, RBP interaction, isoform function).

- **Paper:** [Nature Methods 2026](https://www.nature.com/articles/s41592-026-03064-3)
- **Upstream:** https://github.com/bowang-lab/Orthrus
- **License:** MIT (code + weights)
- **Device:** GPU only — Mamba's selective-scan kernel is CUDA-only in the bundled `mamba_ssm` wheel. Skipped under `-profile cpu` with a warning. Single image variant:
    - `rnazoo-orthrus:latest` (bundles all seven checkpoints — three 4-track + four 6-track)

## What it does

Orthrus is a self-supervised foundation model trained on **32.7 million transcripts** from GENCODE, RefSeq, and Zoonomia ortholog alignments (10 model organisms, 400+ mammalian species), using contrastive learning over splice-isoform pairs and orthologous transcript pairs. The encoder is a Mamba state-space model — unlike transformer-based foundation models (RNA-FM, RiNALMo, ERNIE-RNA) which scale O(L²) in attention memory, Mamba scales linearly in sequence length, so Orthrus handles long mRNAs (>10 kb) without OOM.

## Available variants

The image bundles all seven checkpoints. Select with `--orthrus_variant`:

### 4-track (sequence-only, FASTA input only)

| Variant flag | HuggingFace repo | Embed dim | Notes |
|---|---|---|---|
| `4track` *(default)* | `antichronology/orthrus-4-track` | 512-d | Canonical sequence-only model (Nature Methods publication) |
| `large-4track` | `quietflamingo/orthrus-large-4-track` | 512-d | Alternative 512-d checkpoint |
| `base-4track` | `quietflamingo/orthrus-base-4-track` | 256-d | Smaller/faster; half the embedding size |

All three use one-hot nucleotide encoding (A/C/G/T, 4 channels) and require only a FASTA — no annotation.

### 6-track (FASTA + CDS/splice annotation)

| Variant flag | HuggingFace repo | Embed dim | Objective | Notes |
|---|---|---|---|---|
| `6track` | `antichronology/orthrus-6-track` | 512-d | Contrastive | Canonical 6-track model (Nature Methods publication) |
| `small-6track` | `antichronology/orthrus-small-6-track` | 256-d | Contrastive | Smaller/faster 6-track variant |
| `mlm-6track` | `antichronology/orthrus-mlm-6-track` | 512-d | Contrastive + MLM | Adds masked-language-model head; best for embedding tasks |
| `large-6track` | `quietflamingo/orthrus-large-6-track` | 512-d | Contrastive | Alternative 512-d checkpoint |

6-track variants add two annotation-derived binary channels per position:

| Extra track | Content |
|---|---|
| Track 5 — CDS | 1 at the **first nucleotide of each codon** within the CDS region |
| Track 6 — Splice | 1 at the **last nucleotide of each exon** (5′ splice site in transcript coordinates) |

These require either `--annotation` (pre-computed TSV) or `--gtf` (auto-parsed GTF). See [Annotation input](#annotation-input-for-6-track-variants) below.

## Input format

### FASTA (all variants)

FASTA of **complete mature mRNA sequences** (5'UTR + CDS + 3'UTR, or as much as you have of the spliced transcript). DNA (T) and RNA (U) are both accepted.

**Important:** Orthrus was trained exclusively on full mature transcripts. Partial sequences (e.g. CDS only, single exons, ncRNA fragments) are out-of-distribution and produce embeddings that do not reflect the model's learned mRNA representations. The wrapper warns when sequences are shorter than `--min-len` (default 200 nt) but does not refuse them.

Example (`tests/data/orthrus_test.fa`): two synthetic ~500 nt mature-mRNA-shaped sequences with 5'UTR + ORF + 3'UTR structure.

### Annotation input (for 6-track variants)

6-track variants require one of:

#### Option A — Annotation TSV (`--annotation`)

Tab-separated file with columns:

| Column | Required | Description |
|--------|----------|-------------|
| `name` | yes | Must match the FASTA header (before first space or `\|`); version suffix stripped |
| `cds_start` | yes | 0-based, transcript-relative CDS start position |
| `cds_end` | yes | 0-based, exclusive CDS end position |
| `exon_lengths` | no | Comma-separated exon lengths (e.g. `120,450,230`). If omitted, Track 6 (splice) is all zeros |

```
name	cds_start	cds_end	exon_lengths
ENST00000370316	78	1578	78,450,123,50,899
ENST00000456328	25	1025	25,300,200,500
```

#### Option B — GTF auto-parse (`--gtf`)

Point to a GENCODE or Ensembl GTF (plain or `.gz`). The wrapper parses exon and CDS records for all transcripts found in the FASTA, derives transcript-relative CDS coordinates and exon lengths, and builds both annotation tracks internally. No genome FASTA needed — the FASTA input already contains the spliced transcript sequences.

Transcript IDs are matched by stripping version suffixes (e.g. `ENST00000370316.7` → `ENST00000370316`).

```bash
# FASTA headers like ">ENST00000370316.7|ENSG...|..." are matched automatically
orthrus_predict.py -i transcripts.fa -o out/ --variant 6track --gtf gencode.v47.annotation.gtf.gz
```

## Output format

A directory containing:

- **`sequence_embeddings.npy`**: NumPy array of shape `(N, D)` — one mean-pooled embedding per input sequence. `D=512` for `4track`/`large-4track`/`6track`/`mlm-6track`/`large-6track`; `D=256` for `base-4track`/`small-6track`.
- **`labels.txt`**: one FASTA header per line, matching embedding rows

With `--per-token`:

- **`<label>_tokens.npy`**: per-sequence `(L, D)` array — one embedding per nucleotide position

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe.

```bash
# 4-track (no annotation)
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-orthrus:latest \
  orthrus_predict.py -i /data/input.fa -o /out

# 6-track with annotation TSV
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/annotation.tsv:/data/annotation.tsv \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-orthrus:latest \
  orthrus_predict.py -i /data/input.fa -o /out --variant 6track --annotation /data/annotation.tsv

# 6-track with GTF auto-parse
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/gencode.gtf.gz:/data/annotation.gtf.gz \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-orthrus:latest \
  orthrus_predict.py -i /data/input.fa -o /out --variant 6track --gtf /data/annotation.gtf.gz
```

## Run with Nextflow

```bash
# 4-track
nextflow run main.nf -profile docker,gpu --orthrus_input /path/to/input.fa

# 6-track with annotation TSV
nextflow run main.nf -profile docker,gpu \
  --orthrus_input /path/to/input.fa \
  --orthrus_variant 6track \
  --orthrus_annotation /path/to/annotation.tsv

# 6-track with GTF
nextflow run main.nf -profile docker,gpu \
  --orthrus_input /path/to/input.fa \
  --orthrus_variant 6track \
  --orthrus_gtf /path/to/gencode.gtf.gz
```

Under `-profile cpu` the process logs a warning and skips. Results appear in `results/orthrus/orthrus_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--orthrus_variant` | `4track` | Model variant — see variant table above. |
| `--orthrus_annotation` | `null` | Annotation TSV (name, cds_start, cds_end[, exon_lengths]) for 6-track variants. |
| `--orthrus_gtf` | `null` | GTF/GFF file to auto-derive annotation for 6-track variants. |
| `--orthrus_per_token` | `false` | Also output per-token (L × D) embeddings per sequence. |
| `--orthrus_min_len` | `200` | Warn (don't refuse) when sequences are shorter than this. |

## Reading the output

```python
import numpy as np

embeddings = np.load("orthrus_out/sequence_embeddings.npy")  # (N, D)
labels = open("orthrus_out/labels.txt").read().strip().split("\n")

for label, emb in zip(labels, embeddings):
    print(f"{label}: {emb.shape}")  # (512,) or (256,) depending on variant
```

## Why Mamba (linear memory)

Compared to the transformer foundations in RNAZoo:

| Model | Embedding | Architecture | Memory at L=10k nt |
|-------|-----------|--------------|--------------------|
| RNA-FM | 640-d | Transformer (12-layer) | ~2.5 GB attention matrix |
| RiNALMo | 1280-d | Transformer (33-layer, 650M params) | ~7 GB attention matrix |
| ERNIE-RNA | 768-d | Transformer (12-layer) | ~2.5 GB attention matrix |
| **Orthrus** | **512-d** | **Mamba SSM (6-layer, ~10M params)** | **Linear (~MB scale)** |

For mRNAs >5 kb, Orthrus is often the only foundation model in the zoo that fits on a single consumer GPU.

## Limitations

- **Mature transcripts only.** Partial sequences are out-of-distribution.
- **GPU required.** No CPU fallback in the bundled image.
- **6-track GTF parsing is in-memory.** For very large GTF files (>1 GB) the initial parse may take 30–60 s. Parse once, then reuse the `--annotation` TSV for subsequent runs.
- **Embedding dimension is 512 or 256** depending on variant.

## Fine-tuning

RNAZoo exposes a generic head trainer (linear / MLP / XGBoost, regression or classification) on top of frozen Orthrus embeddings. See the [Fine Tuning guide](../finetuning.md) for input format, head choice, the two execution paths (full chain vs. precomputed embeddings), and worked examples.

The full-chain path is GPU-only because Orthrus inference itself requires CUDA (Mamba SSM kernels). The **precomputed-embeddings path lifts that requirement** — once you have the `.npy`, head training runs on CPU in the dedicated `rnazoo-finetune-head` image.

### Orthrus fine-tuning parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--orthrus_finetune_input` | `null` | TSV/CSV with `name`, `sequence`, label column |
| `--orthrus_finetune_label` | (required) | Column name with target values |
| `--orthrus_finetune_embeddings` | `null` | Precomputed `(N, D)` `.npy` — switches to the head-only path (CPU-OK) |
| `--orthrus_finetune_head_type` | `linear` | `linear`, `mlp`, or `xgboost` (xgboost requires `_embeddings`) |
| `--orthrus_finetune_task` | `auto` | `auto`, `regression`, or `classification` |
| `--orthrus_finetune_epochs` | 20 | Max training epochs (torch heads) |
| `--orthrus_finetune_lr` | 1e-3 | Adam (torch) or XGBoost learning rate |
