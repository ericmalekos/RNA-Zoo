# SpliceBERT

Extract RNA embeddings from a primary-RNA-sequence BERT pretrained on 2M+ vertebrate primary RNAs.

- **Paper:** [Briefings in Bioinformatics 2024](https://doi.org/10.1093/bib/bbae163) — Chen et al., "Self-supervised learning on millions of primary RNA sequences from 72 vertebrates improves sequence-based RNA splicing prediction"
- **Upstream:** [github.com/biomed-AI/SpliceBERT](https://github.com/biomed-AI/SpliceBERT)
- **Weights:** [Zenodo 7995778](https://doi.org/10.5281/zenodo.7995778) (`models.tar.gz`, 217 MB; we ship the `SpliceBERT.1024nt` variant)
- **License:** BSD-3-Clause source + CC-BY-4.0 weights (Zenodo) — clear for public Docker redistribution
- **Device:** CPU or GPU. Two image variants:
    - `rnazoo-splicebert:latest` — CUDA-enabled (default, used with `-profile gpu`)
    - `rnazoo-splicebert-cpu:latest` — CPU-only (smaller, used with `-profile cpu`)

## What it does

SpliceBERT is a 6-layer, 512-dimensional BERT pretrained with masked language modeling on **2M+ primary RNA (pre-mRNA) sequences** drawn from 72 vertebrate species. Architectural details: ~19M parameters, 16 attention heads, single-nucleotide tokenization (vocab `[PAD] [UNK] [CLS] [SEP] [MASK] N A C G T`), absolute position embeddings, 1024 nt context.

Three pretrained variants ship in the upstream Zenodo bundle (`SpliceBERT.510nt`, `SpliceBERT-human.510nt`, `SpliceBERT.1024nt`); RNAZoo uses the `1024nt` broad-pretrain variant for the longest context window and broadest species coverage.

The pipeline currently exposes only the inference path (per-sequence and optional per-token embeddings). Upstream additionally supports fine-tuning for splice-site prediction and branchpoint prediction; that is not yet wired through RNAZoo.

## Input format

FASTA file of RNA sequences using either RNA (A/C/G/U) or DNA (A/C/G/T) alphabets. SpliceBERT was trained on DNA letters; the wrapper automatically converts U → T before tokenization.

**Maximum sequence length: 1024 nt.** SpliceBERT.1024nt has a 1026 max-position-embedding limit; CLS+SEP consume 2 slots, so raw inputs are capped at 1024. Longer sequences are truncated with a warning. The upstream README notes the model "may not work on sequences shorter than 64 nt" since the pretraining distribution was 64–1024 nt.

Example:

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGGGAAGUCCUCGUGUUGCACCUGACUGUCUUUCCGAACGGGCGUUUCUUUUCCUCCGCGCUACCUGCCAGG
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUUAAGCUGUAAGAUGGCAGUAGCUUACUAGGCAGGAAAAGACCCUGUUGAGCUUGACUCUAGUU
```

## Output format

A directory containing:

- **`sequence_embeddings.npy`**: NumPy array of shape `(N, 512)` — one 512-d embedding per input sequence (mean-pooled across non-special positions, matching the convention used by RNA-FM / RiNALMo / RNAErnie / PlantRNA-FM wrappers)
- **`labels.txt`**: one FASTA header per line, in the same order as the embedding rows

With `--per-token`:

- **`<label>_tokens.npy`**: per-sequence NumPy array of shape `(L, 512)` — one 512-d embedding per nucleotide position

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
# CPU
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-splicebert-cpu:latest \
  splicebert_predict.py -i /data/input.fa -o /out

# GPU
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-splicebert:latest \
  splicebert_predict.py -i /data/input.fa -o /out
```

Add `--per-token` to either invocation for per-token embeddings.

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu --splicebert_input /path/to/input.fa

# GPU
nextflow run main.nf -profile docker,gpu --splicebert_input /path/to/input.fa
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/splicebert/splicebert_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--splicebert_per_token` | `false` | Also output per-token (L x 512) embeddings per sequence |
| `--splicebert_max_len` | `1024` | Truncate inputs to this many nt (SpliceBERT.1024nt's positional-embedding cap, 1026 minus CLS+SEP) |
| `--splicebert_batch_size` | `8` | Sequences per forward pass; lower if you hit GPU OOM |

## Reading the output

```python
import numpy as np

embeddings = np.load("splicebert_out/sequence_embeddings.npy")  # (N, 512)
labels = open("splicebert_out/labels.txt").read().strip().split("\n")

for label, emb in zip(labels, embeddings):
    print(f"{label}: {emb.shape}")  # (512,)
```

## Limitations

- **Vertebrate-only training.** Performance on plant, fungal, or bacterial RNA is uncharacterised. For plant work prefer PlantRNA-FM; for general ncRNA prefer RNA-FM / RiNALMo / ERNIE-RNA / RNAErnie.
- **Maximum input length is 1024 nt** — short ncRNAs and short pre-mRNA windows fit; long mRNAs (>1 kb) must be truncated or chunked.
- **Splice-task specialisation isn't yet wired** — upstream provides scripts for splice-site prediction (token classification) and branchpoint prediction; RNAZoo currently exposes only the embedding path. Fine-tune those tasks externally if needed, or open an issue requesting the head wiring.
- **`bert.pooler.dense` warning at load time** is benign — the wrapper mean-pools `last_hidden_state` directly and never invokes the pooler.
