# HydraRNA

**Track:** RNA Foundation Models  
**Paper:** Li et al., *Genome Biology* 2025 — doi:[10.1186/s13059-025-03853-7](https://doi.org/10.1186/s13059-025-03853-7)  
**Upstream repo:** <https://github.com/GuipengLi/HydraRNA>  
**License:** MIT (code + weights)  
**GPU required:** Yes (Mamba CUDA selective-scan kernel; no CPU fallback)

## What it does

HydraRNA is a hybrid bidirectional-SSM + multi-head attention RNA language model
trained on full-length transcripts (up to 10,000 nt). The model stack alternates
between **Hydra** (bidirectional Mamba) blocks and **MHA** blocks (12 layers total),
producing per-token and mean-pooled sequence embeddings (1024-d). It outperforms
comparable models on mRNA-related benchmarks (MRL, half-life, TE) despite fewer
parameters, attributed to the full-length input window and bidirectional SSM context.

The zoo ships the **base model** (`HydraRNA_model.pt`, 337 MB from Zenodo
[10.5281/zenodo.20481998](https://doi.org/10.5281/zenodo.20481998)). The secondary
structure fine-tuned variant (`HydraRNA_model_V2.pt` + `HydraRNA_SS_model.pt`) is
not currently wired.

## Input

A FASTA file of RNA sequences (A/C/G/U or A/C/G/T). Sequences should ideally be
complete mature transcripts; partial or very short sequences will produce
out-of-distribution embeddings. No hard length limit is enforced — sequences longer
than 10,240 nt are split into 10,240-nt chunks and the final embedding is the
mean over chunk embeddings.

**Example test sequence** (`tests/data/test_rna.fa` works):
```
>my_transcript
AUGCUAGCUAGCUAGCUA...
```

## Output

| File | Description |
|------|-------------|
| `sequence_embeddings.npy` | `(N, 1024)` float32 — one row per sequence |
| `labels.txt` | FASTA headers, one per line, matching row order |
| `{header}_tokens.npy` | `(L, 1024)` per-token embeddings (optional; first 10,240 nt only for very long sequences) |

## Docker run

```bash
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/data:/data \
  ghcr.io/ericmalekos/rnazoo-hydrarna:latest \
  hydrarna_predict.py \
    -i /data/sequences.fa \
    -o /data/hydrarna_out
```

With per-token embeddings:
```bash
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/data:/data \
  ghcr.io/ericmalekos/rnazoo-hydrarna:latest \
  hydrarna_predict.py \
    -i /data/sequences.fa \
    -o /data/hydrarna_out \
    --per-token
```

## Nextflow run

```bash
nextflow run ericmalekos/RNA-Zoo \
  --hydrarna_input sequences.fa \
  --outdir results \
  -profile docker,gpu
```

### Linear-probe fine-tuning

```bash
nextflow run ericmalekos/RNA-Zoo \
  --hydrarna_finetune_input labeled.tsv \
  --hydrarna_finetune_label rl \
  --outdir results \
  -profile docker,gpu
```

From precomputed embeddings (no GPU needed for head training):
```bash
nextflow run ericmalekos/RNA-Zoo \
  --hydrarna_finetune_input labeled.tsv \
  --hydrarna_finetune_label rl \
  --hydrarna_finetune_embeddings sequence_embeddings.npy \
  --outdir results \
  -profile docker,cpu
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--hydrarna_input` | `null` | Path to FASTA; activates the HYDRARNA process |
| `--hydrarna_outdir` | `<outdir>/hydrarna` | Output directory |
| `--hydrarna_per_token` | `false` | Emit per-token `.npy` files alongside sequence embeddings |
| `--hydrarna_max_len` | `10000` | Warn (don't fail) for sequences exceeding this length |
| `--hydrarna_finetune_input` | `null` | TSV/CSV with `name`, `sequence`, and a label column |
| `--hydrarna_finetune_label` | `null` | Column name in the fine-tune TSV to use as the label |
| `--hydrarna_finetune_outdir` | `<outdir>/hydrarna_finetune` | Fine-tune output directory |
| `--hydrarna_finetune_epochs` | `20` | Training epochs for the probe head |
| `--hydrarna_finetune_lr` | `1e-3` | Learning rate for the probe head |
| `--hydrarna_finetune_embeddings` | `null` | Precomputed `(N, 1024)` `.npy`; skips embedding extraction |
| `--hydrarna_finetune_head_type` | `linear` | Head architecture: `linear`, `mlp`, or `xgboost` |
| `--hydrarna_finetune_task` | `auto` | `auto`, `regression`, or `classification` |

## Implementation notes

- The model uses **vendored fairseq** (in the upstream repo's `fairseq/` directory).
  The Dockerfile installs it as an editable package alongside the main inference code.
- Tokenization: individual characters separated by spaces, prefixed with `<s>`.
  T→U conversion is applied before tokenization (model vocabulary is ACGU).
- Embeddings are extracted via `model.encoder.extract_features(src_tokens=...)`;
  BOS and EOS tokens are stripped before mean-pooling.
- The model is run in **float16** for inference.
- No CPU variant is provided — the Mamba SSM kernel requires CUDA.
