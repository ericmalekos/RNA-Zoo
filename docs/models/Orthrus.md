# Orthrus

Mamba-based mature mRNA foundation model. Produces 256-dimensional global embeddings from full mRNA sequences for downstream property prediction (half-life, ribosome load, localization, RBP interaction, isoform function).

- **Paper:** [Nature Methods 2026](https://www.nature.com/articles/s41592-026-03064-3)
- **Upstream:** https://github.com/bowang-lab/Orthrus
- **License:** MIT (code + weights)
- **Device:** GPU only — Mamba's selective-scan kernel is CUDA-only in the bundled `mamba_ssm` wheel. Skipped under `-profile cpu` with a warning. Single image variant:
    - `rnazoo-orthrus:latest`

## What it does

Orthrus is a self-supervised foundation model trained on **32.7 million transcripts** from GENCODE, RefSeq, and Zoonomia ortholog alignments (10 model organisms, 400+ mammalian species), using contrastive learning over splice-isoform pairs and orthologous transcript pairs. The encoder is a Mamba state-space model — unlike transformer-based foundation models (RNA-FM, RiNALMo, ERNIE-RNA) which scale O(L²) in attention memory, Mamba scales linearly in sequence length, so Orthrus handles long mRNAs (>10 kb) without OOM.

## Why only 4-track?

Orthrus has two upstream variants and this module ships **only the 4-track v1 model** (`orthrus_v1_4_track`, 256-d output):

| Variant | Channels | Output | What's needed at inference |
|---------|----------|--------|----------------------------|
| **4-track** (bundled) | A, C, G, U one-hot (4) | 256-d | A FASTA. That's it. |
| 6-track | nucleotides (4) + CDS-mask + splice-junction-mask | 512-d | The mature spliced sequence **and** per-position CDS bounds **and** exon-junction positions. Upstream uses GenomeKit, which precompiles a GTF/GFF annotation together with a 2bit reference genome (~1 GB per assembly). |

The 6-track model produces better embeddings on downstream property tasks because it gets told upfront where the protein-coding region is and where introns were spliced out. But the input contract is much heavier: users would need to provide either (a) transcript IDs + a bundled reference genome + annotation, or (b) a custom format that pre-encodes the two extra channels. The 4-track FASTA-in path matches how the rest of the model zoo works (RNA-FM, RiNALMo, ERNIE-RNA all take plain FASTA), so we ship that and revisit 6-track if a user needs it.

## Input format

FASTA of **complete mature mRNA sequences** (5'UTR + CDS + 3'UTR + poly-A, or as much as you have of the spliced transcript). DNA (T) is auto-converted to U at parse time.

**Important:** Orthrus was trained exclusively on full mature transcripts. Partial sequences (e.g. CDS only, single exons, ncRNA fragments) are out-of-distribution and produce embeddings that do not reflect the model's learned mRNA representations. The wrapper warns when sequences are shorter than `--min-len` (default 200 nt) but does not refuse them.

Example (`tests/data/orthrus_test.fa`): two synthetic ~500 nt mature-mRNA-shaped sequences with 5'UTR + ORF + 3'UTR + poly-A structure.

## Output format

A directory containing:

- **`sequence_embeddings.npy`**: NumPy array of shape `(N, 256)` — one 256-d embedding per input sequence (mean-pooled across non-padding positions by `model.representation()`)
- **`labels.txt`**: one FASTA header per line, in the same order as the embedding rows

With `--per-token`:

- **`<label>_tokens.npy`**: per-sequence NumPy array of shape `(L, 256)` — one 256-d embedding per nucleotide position

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
| `--orthrus_variant` | `v1_4_track` | Model variant. Currently only `v1_4_track` is bundled. |
| `--orthrus_per_token` | `false` | Also output per-token (L x 256) embeddings per sequence. |

## Reading the output

```python
import numpy as np

embeddings = np.load("orthrus_out/sequence_embeddings.npy")  # (N, 256)
labels = open("orthrus_out/labels.txt").read().strip().split("\n")

for label, emb in zip(labels, embeddings):
    print(f"{label}: {emb.shape}")  # (256,)
```

## Why Mamba (linear memory)

Compared to the transformer foundations in RNAZoo:

| Model | Embedding | Architecture | Memory at L=10k nt |
|-------|-----------|--------------|--------------------|
| RNA-FM | 640-d | Transformer (12-layer) | ~2.5 GB attention matrix (full attn) |
| RiNALMo | 1280-d | Transformer (33-layer, 650M params) | ~7 GB attention matrix (full attn) |
| ERNIE-RNA | 768-d | Transformer (12-layer) | ~2.5 GB attention matrix (full attn) |
| **Orthrus** | **256-d** | **Mamba SSM (6-layer, ~10M params)** | **Linear (~MB scale)** |

For mRNAs >5 kb, Orthrus is often the only foundation model in the zoo that fits on a single consumer GPU.

## Limitations

- **Mature transcripts only.** Partial sequences are OOD.
- **GPU required.** No CPU fallback in the bundled image.
- **4-track only.** The 6-track variant (which adds CDS/splice tracks for slightly better embeddings) is not exposed; GenomeKit + reference genome staging would be needed to wire it in.
- **Embedding dimension is 256** — smaller than the transformer foundations. This is by design (Mamba SSM hidden dim) but means less granular per-position information than RNA-FM (640) / RiNALMo (1280).
