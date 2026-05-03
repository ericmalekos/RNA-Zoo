# mRNABERT

Extract embeddings from a 12-layer MosaicBERT pretrained on ~18M full-length mRNAs with hybrid per-nt-UTR + per-codon-CDS tokenization. Combines nucleotide-level resolution for untranslated regions with codon-level structure for CDS — distinct from the all-nucleotide foundation models (RNA-FM, RiNALMo, ERNIE-RNA, RNAErnie, PlantRNA-FM) and the all-codon model (CaLM).

- **Paper:** [Nature Communications 2025](https://doi.org/10.1038/s41467-025-65340-8) — Xiong et al., "mRNABERT: advancing mRNA sequence design with a universal language model and comprehensive dataset"
- **GitHub:** [`yyly6/mRNABERT`](https://github.com/yyly6/mRNABERT) · **HF model:** [`YYLY66/mRNABERT`](https://huggingface.co/YYLY66/mRNABERT)
- **License:** Apache-2.0 (code + weights, per HF YAML)
- **Device:** CPU or GPU. Two image variants:
    - `rnazoo-mrnabert:latest` — CUDA-enabled (default, used with `-profile gpu`); uses the upstream Triton-based flash-attention path
    - `rnazoo-mrnabert-cpu:latest` — CPU-only; the model's `bert_layers.py` falls back to plain PyTorch attention when triton can't be imported

## What it does

mRNABERT is a 12-layer / 768-dim MosaicBERT (Apache-2.0) pretrained on ~18M curated full-length mRNA sequences from across the tree of life. The novel design choice is its **hybrid tokenization**: the 5'/3' UTRs are tokenized at single-nucleotide resolution (A, T, C, G, N) while the CDS region is tokenized at codon resolution (64 codons). The 74-token vocab is the union: 5 specials + 5 single-letter UTR tokens + 64 codons.

The model uses **ALiBi positional embeddings** instead of absolute positions, which allows length extrapolation beyond the 512-token training context to ~1024 tokens at inference (the tokenizer's `model_max_length`). The wrapper truncates longer inputs.

## Input format

Standard FASTA of mRNA sequences. The wrapper:

- Uppercases and converts U → T (mRNABERT's vocab is DNA-style, T not U).
- **Auto-detects the longest ORF** in each sequence using upstream's logic (`data_process/process_pretrain_data.py:find_longest_cds`) — finds the longest ATG…STOP frame, treats it as CDS, and treats flanking regions as UTR. No CDS coordinates required from the user.
- If no ORF is detected, the entire sequence is treated as UTR (single-letter tokenization).
- Truncates inputs whose tokenized length exceeds 1024 tokens (after CLS/SEP).

Example (reuses `tests/data/rnafm_test.fa` for the smoke test — note that `test_rna_1` has no in-frame stop and thus no detectable ORF, so it's tokenized as all-UTR; `test_rna_2` has a tiny 18-nt ORF that gets codon-tokenized):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGGGAAGUCCUCGUGUUGCACCUGACUGUCUUUCCGAACGGGCGUUUCUUUUCCUCCGCGCUACCUGCCAGG
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUUAAGCUGUAAGAUGGCAGUAGCUUACUAGGCAGGAAAAGACCCUGUUGAGCUUGACUCUAGUU
```

## Output format

A directory containing:

- **`sequence_embeddings.npy`**: NumPy array of shape `(N, 768)` — one 768-d embedding per input sequence (mean-pooled across token positions, excluding `[CLS]` and `[SEP]`)
- **`labels.txt`**: one FASTA header per line, in the same order as the embedding rows

With `--per-token`:

- **`<label>_tokens.npy`**: per-sequence NumPy array of shape `(T, 768)` — one 768-d embedding per token **including** `[CLS]` (row 0) and `[SEP]` (last row), where T is the number of tokens (codon-tokenized CDS counts as 1 token per codon, not 1 per nt)

> **Pooling note.** This wrapper mean-pools excluding CLS/SEP, matching the RNAZoo foundation-tier convention (RNA-FM, RiNALMo, RNAErnie, PlantRNA-FM, CaLM). The upstream README example uses a simpler mean-with-CLS+SEP — pool yourself from `--per-token` output if you need exact upstream parity.

## Run with Docker

```bash
# CPU (uses PyTorch attention fallback)
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-mrnabert-cpu:latest \
  mrnabert_predict.py -i /data/input.fa -o /out

# GPU (uses Triton-based flash-attention)
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-mrnabert:latest \
  mrnabert_predict.py -i /data/input.fa -o /out
```

Add `--per-token` to either invocation for per-token embeddings.

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu --mrnabert_input /path/to/input.fa

# GPU
nextflow run main.nf -profile docker,gpu --mrnabert_input /path/to/input.fa
```

Results land in `results/mrnabert/mrnabert_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--mrnabert_per_token` | `false` | Also output per-token (T x 768) embeddings per sequence |

## Reading the output

```python
import numpy as np

embeddings = np.load("mrnabert_out/sequence_embeddings.npy")  # (N, 768)
labels = open("mrnabert_out/labels.txt").read().strip().split("\n")

for label, emb in zip(labels, embeddings):
    print(f"{label}: {emb.shape}")  # (768,)
```

## Comparison with the other foundation models in the zoo

| Model | Tokenization | Embedding | Pretraining set | Position encoding |
|-------|--------------|-----------|-----------------|-------------------|
| RNA-FM | Single nt | 640-d | 23M ncRNAs (RNAcentral) | Absolute (max 1022 nt) |
| RiNALMo | Single nt | 1280-d | 36M ncRNAs (RNAcentral) | Absolute |
| ERNIE-RNA | Single nt | 768-d | 20M ncRNAs (RNAcentral) | Absolute (max 1022 nt) |
| RNAErnie | Single nt | 768-d | 23M ncRNAs (RNAcentral) | Absolute (max 2046 nt) |
| Orthrus | Single nt (Mamba) | 512-d | 32.7M mRNAs (GENCODE+RefSeq) | None (state-space) |
| PlantRNA-FM | Single nt | 480-d | ~25M plant RNAs | Rotary (max 1024 nt) |
| CaLM | Codon (3-letter) | 768-d | ~9M CDSs (cross-organism) | Rotary (max 1024 codons) |
| **mRNABERT** | **Hybrid: 1-nt UTR + 3-nt CDS codons** | **768-d** | **~18M full-length mRNAs** | **ALiBi (extrapolates beyond 512 to 1024)** |

mRNABERT is the only zoo model that tokenizes UTR and CDS regions differently — preserving codon-frame structure where it exists while keeping nucleotide resolution where it doesn't. For full-length mRNA design, expression prediction, or any task where the UTR/CDS distinction matters, this is the natural inductive bias.

## Limitations

- **CDS detection by ORF length only.** The wrapper picks the longest ATG…STOP frame; if the true CDS is shorter than a spurious upstream ORF, the wrong region gets codon-tokenized. For research-grade work, supply pre-trimmed UTR and CDS sequences and let the wrapper auto-detect.
- **Length cap is 1024 tokens** post-tokenization (after CLS+SEP overhead, ~1022 effective). An mRNA with 200-nt 5'UTR + 600-nt CDS + 200-nt 3'UTR tokenizes to 200 + 200 + 200 = 600 tokens — comfortable. An mRNA with 4 kb of UTRs would exceed it; the wrapper truncates with a warning.
- **Pooler weights are uninitialized in the released checkpoint** — this triggers a benign warning at load. The wrapper uses mean-pool over `last_hidden_state`, not `pooler_output`, so the missing weights don't affect outputs. Don't use `model.pooler` directly.
- **Inference-only.** Upstream `run_mlm.py` exists for continued MLM pretraining and downstream fine-tuning, but neither is exposed through the pipeline yet.

## Fine-tuning (linear probe)

For supervised tasks on user-labeled data, RNA-Zoo exposes a **linear-probe fine-tune** for mRNABERT: the backbone stays frozen, and a small MLP head trains on top of the 768-d embeddings. This is the de facto standard for foundation models — same pattern Orthrus and HydraRNA use upstream. Backbone fine-tuning is out of scope here (separate per-model design; UTR-LM's pattern is the closest existing reference but only feasible for small backbones).

### Input format

TSV or CSV with required columns `name`, `sequence`, and a numeric label column. Example:

```
name<TAB>sequence<TAB>te
seq_001<TAB>GGGUGCGAU...<TAB>1.42
seq_002<TAB>AUUCCGAGA...<TAB>0.87
```

### Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu   # or gpu \
  --mrnabert_finetune_input my_labels.tsv \
  --mrnabert_finetune_label te
```

Device: CPU or GPU (uses the inference image). The fine-tune reuses the inference image — no new Docker image to pull.

Outputs land in `results/mrnabert_finetune/mrnabert_finetune_out/`:

- **`best_head.pt`** — trained MLP head (state_dict + config dict including label mean/std for inverse-transform at predict time)
- **`predictions.tsv`** — predictions for every input row, with `train`/`val` split annotation
- **`metrics.json`** — overall + train + val MSE / R² / Pearson r / Spearman r

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--mrnabert_finetune_label` | (required) | Column name in input TSV/CSV |
| `--mrnabert_finetune_epochs` | 20 | Max training epochs (early-stop patience 5) |
| `--mrnabert_finetune_lr` | 1e-3 | Adam learning rate |

### Fine-tune from precomputed embeddings (skip predict)

If you've already run inference and saved `sequence_embeddings.npy`, you can skip the backbone forward pass and feed those embeddings directly into the head trainer — useful when iterating on head training (different epochs / lr / labels) without re-paying the predict cost.

```bash
nextflow run main.nf -profile docker,cpu \
  --mrnabert_finetune_input my_labels.tsv \
  --mrnabert_finetune_label te \
  --mrnabert_finetune_embeddings my_embeddings.npy
```

When `--mrnabert_finetune_embeddings` is set, the workflow skips `mrnabert_predict.py` and uses the supplied `(N, D)` `.npy` directly. The TSV still supplies `name` and the label column; the `sequence` column is optional and ignored. Row order in the `.npy` must match row order in the TSV — the head trainer exits with an error if shapes disagree.

Outputs land in the same `mrnabert_finetune_out/` directory with the same files (`best_head.pt`, `predictions.tsv`, `metrics.json`) as the full-chain mode.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--mrnabert_finetune_embeddings` | `null` | Optional precomputed `(N, D)` `.npy`; when set, skips predict |
| `--mrnabert_finetune_head_type` | `linear` | `linear` (strict probe), `mlp` (2-layer), or `xgboost` (requires `_embeddings`) |
| `--mrnabert_finetune_task` | `auto` | `auto`, `regression`, or `classification`; auto-detects from labels |
