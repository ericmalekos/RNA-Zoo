# Orthrus

Mamba-based mature mRNA foundation model. Produces 256-d or 512-d global embeddings from full mRNA sequences for downstream property prediction (half-life, ribosome load, localization, RBP interaction, isoform function).

- **Paper:** [Nature Methods 2026](https://www.nature.com/articles/s41592-026-03064-3)
- **Upstream:** https://github.com/bowang-lab/Orthrus
- **License:** MIT (code + weights)
- **Device:** GPU only — Mamba's selective-scan kernel is CUDA-only in the bundled `mamba_ssm` wheel. Skipped under `-profile cpu` with a warning. Single image variant:
    - `rnazoo-orthrus:latest` (bundles all three 4-track checkpoints, ~390 MB weights)

## What it does

Orthrus is a self-supervised foundation model trained on **32.7 million transcripts** from GENCODE, RefSeq, and Zoonomia ortholog alignments (10 model organisms, 400+ mammalian species), using contrastive learning over splice-isoform pairs and orthologous transcript pairs. The encoder is a Mamba state-space model — unlike transformer-based foundation models (RNA-FM, RiNALMo, ERNIE-RNA) which scale O(L²) in attention memory, Mamba scales linearly in sequence length, so Orthrus handles long mRNAs (>10 kb) without OOM.

## Available variants

The image bundles all three 4-track standardized checkpoints. Select with `--orthrus_variant`:

| Variant flag | HuggingFace repo | Embed dim | Notes |
|---|---|---|---|
| `4track` *(default)* | `antichronology/orthrus-4-track` | 512-d | Canonical sequence-only model |
| `large-4track` | `quietflamingo/orthrus-large-4-track` | 512-d | Alternative 512-d checkpoint |
| `base-4track` | `quietflamingo/orthrus-base-4-track` | 256-d | Smaller/faster; half the embedding size |

All three use one-hot nucleotide encoding only (A/C/G/T, 4 channels) and take a plain FASTA — no annotation required.

### Why no 6-track variants?

The 6-track models add two annotation-derived channels per position:

| Extra track | Content | Source |
|---|---|---|
| Track 5 — CDS | Binary: 1 at the first nucleotide of each codon | CDS start/end + reading frame |
| Track 6 — Splice | Binary: 1 at 5′ splice sites | Intron/exon structure |

These channels are **not derivable from sequence alone** and require per-transcript CDS coordinates and splice junction annotation. The upstream examples use GenomeKit, which precompiles a GTF/GFF annotation against a 2bit reference genome (~1 GB per assembly) into a queryable index. Wiring that into the zoo would require a new input contract (FASTA + GTF or pre-built 6-track arrays) that breaks the uniform FASTA-in interface shared by RNA-FM, RiNALMo, ERNIE-RNA, and RNAErnie.

**Future work:** 6-track support is planned. The most practical path is accepting a second optional input — a TSV of `(transcript_id, cds_start, cds_end, splice_sites)` — that the wrapper uses to build the extra channels before encoding. If you need this, open an issue.

## Input format

FASTA of **complete mature mRNA sequences** (5'UTR + CDS + 3'UTR + poly-A, or as much as you have of the spliced transcript). DNA (T) is auto-converted to U at parse time.

**Important:** Orthrus was trained exclusively on full mature transcripts. Partial sequences (e.g. CDS only, single exons, ncRNA fragments) are out-of-distribution and produce embeddings that do not reflect the model's learned mRNA representations. The wrapper warns when sequences are shorter than `--min-len` (default 200 nt) but does not refuse them.

Example (`tests/data/orthrus_test.fa`): two synthetic ~500 nt mature-mRNA-shaped sequences with 5'UTR + ORF + 3'UTR + poly-A structure.

## Output format

A directory containing:

- **`sequence_embeddings.npy`**: NumPy array of shape `(N, D)` — one embedding per input sequence (mean-pooled across non-padding positions by `model.representation()`). `D=512` for `4track`/`large-4track`; `D=256` for `base-4track`.
- **`labels.txt`**: one FASTA header per line, in the same order as the embedding rows

With `--per-token`:

- **`<label>_tokens.npy`**: per-sequence NumPy array of shape `(L, D)` — one embedding per nucleotide position

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe.

```bash
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-orthrus:latest \
  orthrus_predict.py -i /data/input.fa -o /out
```

Add `--per-token` for per-token embeddings.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,gpu --orthrus_input /path/to/input.fa
```

Under `-profile cpu` the process logs a warning and skips. Results appear in `results/orthrus/orthrus_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--orthrus_variant` | `4track` | Model variant: `4track` (512-d), `large-4track` (512-d), `base-4track` (256-d). |
| `--orthrus_per_token` | `false` | Also output per-token (L x D) embeddings per sequence. |
| `--orthrus_min_len` | `200` | Warn (don't refuse) when sequences are shorter than this — Orthrus is mature-mRNA only, fragments are out-of-distribution. |

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
| RNA-FM | 640-d | Transformer (12-layer) | ~2.5 GB attention matrix (full attn) |
| RiNALMo | 1280-d | Transformer (33-layer, 650M params) | ~7 GB attention matrix (full attn) |
| ERNIE-RNA | 768-d | Transformer (12-layer) | ~2.5 GB attention matrix (full attn) |
| **Orthrus** | **512-d** | **Mamba SSM (6-layer, ~10M params)** | **Linear (~MB scale)** |

For mRNAs >5 kb, Orthrus is often the only foundation model in the zoo that fits on a single consumer GPU.

## Limitations

- **Mature transcripts only.** Partial sequences are OOD.
- **GPU required.** No CPU fallback in the bundled image.
- **4-track only.** The 6-track variants (which add CDS/splice tracks for slightly better embeddings) are not yet exposed — see the "Why no 6-track variants?" section above for the planned path.
- **Embedding dimension is 512 or 256** depending on variant — 512-d is smaller than RiNALMo (1280) and ERNIE-RNA (768), comparable to RNA-FM (640). The SSM hidden dim is fixed by the architecture.

## Fine-tuning

RNAZoo exposes a generic head trainer (linear / MLP / XGBoost, regression or classification) on top of frozen Orthrus embeddings (512-d for `4track`/`large-4track`, 256-d for `base-4track`). See the [Fine Tuning guide](../finetuning.md) for input format, head choice, the two execution paths (full chain vs. precomputed embeddings), and worked examples.

The full-chain path is GPU-only here because Orthrus inference itself requires CUDA (Mamba SSM kernels). The **precomputed-embeddings path lifts that requirement** — once you have the `.npy`, head training runs on CPU in the dedicated `rnazoo-finetune-head` image.

### Orthrus-specific parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--orthrus_finetune_input` | `null` | TSV/CSV with `name`, `sequence`, label column |
| `--orthrus_finetune_label` | (required) | Column name with target values |
| `--orthrus_finetune_embeddings` | `null` | Precomputed `(N, D)` `.npy` — switches to the head-only path (CPU-OK) |
| `--orthrus_finetune_head_type` | `linear` | `linear`, `mlp`, or `xgboost` (xgboost requires `_embeddings`) |
| `--orthrus_finetune_task` | `auto` | `auto`, `regression`, or `classification` |
| `--orthrus_finetune_epochs` | 20 | Max training epochs (torch heads) |
| `--orthrus_finetune_lr` | 1e-3 | Adam (torch) or XGBoost learning rate |
