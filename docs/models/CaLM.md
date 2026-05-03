# CaLM

Extract codon-level embeddings from a 12-layer transformer pretrained on cross-organism CDS sequences. Complementary to CodonTransformer (which is generative): CaLM produces representations, CodonTransformer optimizes codon usage.

- **Paper:** [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00791-0) — Outeiral & Deane, "Codon language embeddings provide strong signals for use in protein engineering"
- **GitHub:** [`oxpig/CaLM`](https://github.com/oxpig/CaLM)
- **License:** BSD-3-Clause (code + weights)
- **Device:** CPU or GPU. Two image variants:
    - `rnazoo-calm:latest` — CUDA-enabled (default, used with `-profile gpu`)
    - `rnazoo-calm-cpu:latest` — CPU-only (smaller, used with `-profile cpu`)

## What it does

CaLM is a 12-layer, 768-dimensional codon-level transformer (~86M params) pretrained on millions of CDSs from across the tree of life. Unlike single-nucleotide RNA LMs (RNA-FM, RiNALMo, ERNIE-RNA, PlantRNA-FM), CaLM tokenizes the input as in-frame **3-letter codons** and treats each codon as an atomic unit — which preserves coding-frame structure that gets lost under nucleotide tokenization.

Input is up to **1024 codons** (~3 kb of CDS); 64 codons + a few special tokens make up the vocabulary. The model uses rotary position embeddings (no fixed positional limit beyond the 1024-codon training window).

Where it slots in: CaLM embeddings have been shown to carry strong signal for protein-engineering downstream tasks — e.g. predicting protein expression, solubility, melting temperature — directly from coding sequence. Pair this with CodonTransformer (generative codon optimization) for an embedding+design loop.

## Input format

FASTA file of RNA / CDS sequences. The wrapper:

- Uppercases the input and converts T → U automatically.
- Trims any sequence that is not a multiple of 3 nucleotides to the largest codon-aligned prefix (with a warning).
- Truncates inputs longer than 1024 codons (3072 nt) (with a warning).

Example (reuses `tests/data/rnafm_test.fa` for the in-pipeline smoke test):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGGGAAGUCCUCGUGUUGCACCUGACUGUCUUUCCGAACGGGCGUUUCUUUUCCUCCGCGCUACCUGCCAGG
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUUAAGCUGUAAGAUGGCAGUAGCUUACUAGGCAGGAAAAGACCCUGUUGAGCUUGACUCUAGUU
```

## Output format

A directory containing:

- **`sequence_embeddings.npy`**: NumPy array of shape `(N, 768)` — one 768-d embedding per input sequence (mean-pooled across codon positions, excluding `<cls>` and `<eos>`)
- **`labels.txt`**: one FASTA header per line, in the same order as the embedding rows

With `--per-token`:

- **`<label>_tokens.npy`**: per-sequence NumPy array of shape `(L+2, 768)` — one 768-d embedding per codon position **including** `<cls>` (row 0) and `<eos>` (last row), so L+2 rows for an L-codon input

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
# CPU
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-calm-cpu:latest \
  calm_predict.py -i /data/input.fa -o /out

# GPU
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-calm:latest \
  calm_predict.py -i /data/input.fa -o /out
```

Add `--per-token` to either invocation for per-codon embeddings.

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu --calm_input /path/to/input.fa

# GPU
nextflow run main.nf -profile docker,gpu --calm_input /path/to/input.fa
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/calm/calm_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--calm_per_token` | `false` | Also output per-codon (L+2 x 768) embeddings per sequence |

## Reading the output

```python
import numpy as np

embeddings = np.load("calm_out/sequence_embeddings.npy")  # (N, 768)
labels = open("calm_out/labels.txt").read().strip().split("\n")

for label, emb in zip(labels, embeddings):
    print(f"{label}: {emb.shape}")  # (768,)
```

## Comparison with the other foundation models in the zoo

| Model | Embedding | Pooling | Tokenization | Training set | Max input | Bundled license |
|-------|-----------|---------|--------------|--------------|-----------|-----------------|
| RNA-FM | 640-d | Mean (excl CLS+EOS) | Single nt | 23M ncRNAs (RNAcentral) | 1022 nt | MIT |
| RiNALMo | 1280-d | Mean (excl CLS+EOS) | Single nt | 36M ncRNAs (RNAcentral) | ~11k nt (memory-bound) | Apache-2.0 |
| ERNIE-RNA | 768-d | [CLS] | Single nt | 20M ncRNAs (RNAcentral) | 1022 nt | MIT |
| RNAErnie | 768-d | Mean (excl CLS+SEP) | Single nt | 23M ncRNAs (RNAcentral) | 2046 nt | Apache-2.0 |
| Orthrus | 512-d | Mean (`mean_unpadded`) | Single nt (Mamba SSM) | 32.7M mRNAs (GENCODE+RefSeq) | unbounded (linear mem) | MIT |
| PlantRNA-FM | 480-d | Mean (excl CLS+EOS) | Single nt | ~25M plant RNAs (1124 species) | 1024 nt | MIT |
| **CaLM** | **768-d** | **Mean (excl CLS+EOS)** | **Codon (3-letter)** | **Cross-organism CDSs (ENA codingseqs)** | **1024 codons (~3 kb)** | **BSD-3-Clause** |

CaLM is the zoo's only **codon-level** foundation model. The other six tokenize at the nucleotide level — which loses reading-frame structure unless the downstream head reconstructs it. For protein-engineering and CDS-level tasks (translation efficiency, expression, solubility, thermal stability), codon tokenization is the natural inductive bias.

Pairing notes:

- **CodonTransformer** (in the Translation track) is generative — given a protein it produces optimized DNA. CaLM is the embedding counterpart — given a CDS it produces a fixed-dim representation. Use both for design + scoring loops.
- **For non-coding RNA**, prefer the nt-tokenized models. CaLM's pretraining data is CDSs; non-coding sequences fall outside its training distribution.

## Limitations

- **Codon-aligned input required.** Sequences whose length is not a multiple of 3 are trimmed to the largest codon-aligned prefix; if your sequence has 5'UTR + CDS + 3'UTR concatenated without removing the UTRs, CaLM will treat the whole thing as codons and the embedding will be partly noise. Strip the UTRs first.
- **Maximum 1024 codons** (~3 kb). Longer CDSs are truncated. For long mRNAs use Orthrus (Mamba, linear memory).
- **Inference-only.** Upstream `training.py` exists for from-scratch pretraining but no fine-tuning recipe is shipped — fine-tuning support is not currently exposed in the pipeline.

## Fine-tuning (linear probe)

For supervised tasks on user-labeled data, RNA-Zoo exposes a **linear-probe fine-tune** for CaLM: the backbone stays frozen, and a small MLP head trains on top of the 768-d embeddings. This is the de facto standard for foundation models — same pattern Orthrus and HydraRNA use upstream. Backbone fine-tuning is out of scope here (separate per-model design; UTR-LM's pattern is the closest existing reference but only feasible for small backbones).

### Input format

TSV or CSV with required columns `name`, `sequence`, and a numeric label column. Example:

```
name<TAB>sequence<TAB>te
seq_001<TAB>GGGUGCGAU...<TAB>1.42
seq_002<TAB>AUUCCGAGA...<TAB>0.87
```

### Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu       # or gpu \
  --calm_finetune_input my_labels.tsv \
  --calm_finetune_label te
```

Device: CPU or GPU (uses the inference image). The fine-tune reuses the inference image — no new Docker image to pull.

Outputs land in `results/calm_finetune/calm_finetune_out/`:

- **`best_head.pt`** — trained MLP head (state_dict + config dict including label mean/std for inverse-transform at predict time)
- **`predictions.tsv`** — predictions for every input row, with `train`/`val` split annotation
- **`metrics.json`** — overall + train + val MSE / R² / Pearson r / Spearman r

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--calm_finetune_label` | (required) | Column name in input TSV/CSV |
| `--calm_finetune_epochs` | 20 | Max training epochs (early-stop patience 5) |
| `--calm_finetune_lr` | 1e-3 | Adam learning rate |
