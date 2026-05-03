# HydraRNA

Full-length RNA language model. 12-layer hybrid Hydra (Mamba-style state-space model) with 2 attention layers, pretrained on ~73M ncRNAs and ~22M protein-coding mRNAs in fairseq's masked_lm_span task. Supports up to **10K nt at inference** — the longest context window in the zoo, achieved via state-space's linear-time scaling.

- **Paper:** [Genome Biology 2025](https://doi.org/10.1186/s13059-025-03853-7) — Li et al., "HydraRNA: a hybrid architecture based full-length RNA language model"
- **GitHub:** [`GuipengLi/HydraRNA`](https://github.com/GuipengLi/HydraRNA)
- **License:** MIT (LICENSE file declares MIT terms; copyright header has a "GPL" typo but the body is unambiguous MIT)
- **Device:** GPU only. Auto-skipped under `-profile cpu` with a warning.
    - `rnazoo-hydrarna:latest` — single image, ~7 GB compressed (target — see "Limitations" for redistribution status)
    - No CPU image (Mamba SSM + flash-attention + Hydra layers all require CUDA at import)

## What it does

HydraRNA's distinguishing feature is **length**. Where most foundation models cap inputs at 1-2 kb (RNA-FM 1022 nt, RNAErnie 2046 nt, PlantRNA-FM 1024 nt, CaLM 1024 codons, mRNABERT 1024 tokens), HydraRNA processes up to **10,240 nucleotides per chunk** — typical full-length human mRNAs (~2 kb median, up to 100+ kb) fit comfortably. Sequences longer than 10K are auto-chunked and the embeddings are averaged across chunks.

Architecturally it's a 12-layer encoder where layers 1-5 and 7-11 are Hydra (Mamba SSM) blocks and layers 6, 12 are MHA attention. ~84M parameters. The state-space layers give linear memory in sequence length; attention layers give bidirectional information mixing.

Per the upstream paper benchmark, HydraRNA wins 8/10 head-to-head comparisons against RNA-FM, RiNALMo, RNAErnie, 3'UTRBERT, and UTR-LM (loses splice-site prediction to RiNALMo).

## Input format

Standard FASTA of RNA sequences. The wrapper:

- Uppercases and converts U → T (HydraRNA's tokenizer is DNA-style, T not U).
- Tokenizes character-by-character (A/T/C/G/N + IUPAC ambiguity codes per `dict/dict.txt`).
- Prepends `<s>` BOS token (per upstream `extract_HydraAttRNA12_5UTRMRL.py`).
- For sequences longer than 10,240 nt, splits into 10K-nt chunks; the per-sequence embedding is the mean of per-chunk means.

## Output format

A directory containing:

- **`sequence_embeddings.npy`**: NumPy array of shape `(N, 1024)` — one 1024-d embedding per input sequence (mean-pooled across positions excluding BOS+EOS, then mean across chunks for inputs > 10K nt)
- **`labels.txt`**: one FASTA header per line, in the same order as the embedding rows

With `--per-token`:

- **`<label>_tokens.npy`**: per-sequence NumPy array of shape `(N+2, 1024)` — per-token embeddings **including** BOS (row 0) and EOS (last row). For inputs > 10K nt, only the last chunk's per-token embedding is saved (full-sequence per-token across chunks would conflate boundaries).

## Run with Docker

```bash
# GPU only (no CPU image)
# NOTE: rnazoo-hydrarna:latest is not yet on ghcr.io because the upstream
# weights are Google-Drive-only — must be locally baked. See "Limitations".
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -u $(id -u):$(id -g) \
  -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  rnazoo-hydrarna:local-test \
  hydrarna_predict.py -i /data/input.fa -o /out
```

Add `--per-token` for per-token embeddings, `--no-half` to disable fp16.

## Run with Nextflow

```bash
# GPU only — HydraRNA auto-skips under -profile cpu
nextflow run main.nf -profile docker,gpu --hydrarna_input /path/to/input.fa
```

Results land in `results/hydrarna/hydrarna_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--hydrarna_per_token` | `false` | Also output per-token (N+2 x 1024) embeddings |
| `--hydrarna_no_half` | `false` | Disable `model.half()` — use full fp32 instead of fp16 (slower but more accurate; useful for debugging fp16 issues) |

## Comparison with the other foundation models in the zoo

| Model | Architecture | Embedding | Max context | Training set | Length scaling |
|-------|--------------|-----------|-------------|--------------|----------------|
| RNA-FM | 12L Transformer | 640-d | 1022 nt | 23M ncRNAs | quadratic |
| RiNALMo | 33L Transformer (650M) | 1280-d | ~11 kb (memory-bound) | 36M ncRNAs | quadratic |
| ERNIE-RNA | 12L Transformer + 2D | 768-d | 1022 nt | 20M ncRNAs | quadratic |
| Orthrus | 6L Mamba SSM | 512-d | unbounded (linear mem) | 32.7M mRNAs | linear |
| RNAErnie | 12L Transformer | 768-d | 2046 nt | 23M ncRNAs | quadratic |
| PlantRNA-FM | 12L ESM | 480-d | 1024 nt | ~25M plant RNAs | quadratic (rotary) |
| CaLM | 12L codon-level | 768-d | 1024 codons (~3 kb) | ~9M CDSs | quadratic |
| mRNABERT | 12L MosaicBERT + ALiBi | 768-d | 1024 tokens | ~18M mRNAs | extrapolated |
| **HydraRNA** | **12L hybrid Hydra-SSM + 2 MHA** | **1024-d** | **10K nt** | **~73M ncRNAs + ~22M mRNAs** | **linear (SSM) + quadratic (2 attn layers)** |

HydraRNA and Orthrus are the two SSM-based models in the zoo. Orthrus is mRNA-focused and uses a contrastive objective; HydraRNA is a generic RNA LM trained with masked_lm_span. For full-length mRNA work where you want a single embedding per transcript without chunking, HydraRNA is the natural choice.

## Limitations

- **GPU-only.** Mamba SSM kernels require CUDA at import. Auto-skipped under `-profile cpu` with a warning. Auto-skip mirrors Orthrus / DRfold2 / seq2ribo.
- **Redistribution blocker.** Upstream weights are distributed only via Google Drive — there is no Hugging Face mirror, no Zenodo release, no GitHub releases artifact. The build context for this image must include the locally-downloaded `HydraRNA_model.pt` (~337 MB). Build it on a host with the weights:

  ```bash
  # 1. Download the weight file (one-time, ~30 sec via gdown)
  pip install --user gdown
  mkdir -p ~/hydrarna_weights_local
  gdown 1NPMhRF5IFDyAkk_X8oA3DhSToh6HTIRM -O ~/hydrarna_weights_local/HydraRNA_model.pt

  # 2. Build the image with the weights as a named build context
  docker build \
    --build-context hydrarna_weights=$HOME/hydrarna_weights_local \
    -f Dockerfiles/Dockerfile.HydraRNA \
    -t rnazoo-hydrarna:local-test .
  ```

  The `publish-images.yml` GitHub Actions workflow has a commented-out matrix entry for `rnazoo-hydrarna` — re-enable it once the weights are mirrored to a permanent public location (HF or Zenodo). Until then, no `:latest` tag exists on ghcr.io.

- **Bundled fairseq.** Upstream vendors a fork of fairseq inside the repo (under `fairseq/`); the image installs it via `pip install --no-build-isolation -e .`. This is fine but means the image is ~7 GB compressed.

- **mamba-ssm 2.2.2 wheel pin.** The image uses the prebuilt `cu118torch2.3cxx11abiFALSE-cp39-cp39` wheel from state-spaces/mamba's release page; if upstream changes their wheel naming convention, the build will break.

- **Flash-Attention 2 fallback for Turing GPUs.** The 2 attention layers (positions 6 and 12) use FlashAttention 2 by default, which requires Ampere or newer (compute capability ≥ 8.0). On Turing (RTX 20xx, GTX 16xx) FlashAttention's CUDA kernel raises `RuntimeError: FlashAttention only supports Ampere GPUs or newer`. The wrapper auto-patches the loaded model after `checkpoint_utils.load_model_ensemble`: it walks every MHA module, replaces `inner_attn` (a `FlashSelfAttention`) with the upstream-shipped `SelfAttention` (plain torch SDPA), and clears `use_flash_attn` on the parent. Numerically equivalent (within float32 round-off); roughly 1.5-2× slower than flash on Ampere+. The patch is idempotent — Ampere+ GPUs see the same code path as Turing, just slightly slower. Disable by removing the patch block in `bin/hydrarna_predict.py` if you have an Ampere+ GPU and want the original throughput.

- **Inference-only.** Upstream `examples/finetune_HydraAttRNA12_mlp_5UTRMRL_scaled.py` shows MLP fine-tuning on user data, but neither continued pretraining nor task-specific heads are exposed through the pipeline.

- **Long-input memory.** A 4 GB consumer GPU may OOM on inputs > 5K nt even with fp16. Try shorter chunks if you hit OOM (the wrapper currently uses the upstream's 10240 chunk size).

## Fine-tuning

RNAZoo exposes a generic head trainer (linear / MLP / XGBoost, regression or classification) on top of frozen 1024-d HydraRNA embeddings. See the [Fine Tuning guide](../finetuning.md) for input format, head choice, the two execution paths (full chain vs. precomputed embeddings), and worked examples.

The full-chain path is GPU-only here because HydraRNA inference itself requires CUDA (Mamba-Hydra SSM kernels + flash-attention). The **precomputed-embeddings path lifts that requirement** — once you have the `.npy`, head training runs on CPU in the dedicated `rnazoo-finetune-head` image. Especially valuable here since HydraRNA is full-length and re-embedding is the slowest step.

### HydraRNA-specific parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--hydrarna_finetune_input` | `null` | TSV/CSV with `name`, `sequence`, label column |
| `--hydrarna_finetune_label` | (required) | Column name with target values |
| `--hydrarna_finetune_embeddings` | `null` | Precomputed `(N, D)` `.npy` — switches to the head-only path (CPU-OK) |
| `--hydrarna_finetune_head_type` | `linear` | `linear`, `mlp`, or `xgboost` (xgboost requires `_embeddings`) |
| `--hydrarna_finetune_task` | `auto` | `auto`, `regression`, or `classification` |
| `--hydrarna_finetune_epochs` | 20 | Max training epochs (torch heads) |
| `--hydrarna_finetune_lr` | 1e-3 | Adam (torch) or XGBoost learning rate |
