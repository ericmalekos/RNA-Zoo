# PlantRNA-FM

Extract RNA embeddings from a language model pretrained on plant transcriptomes.

- **Paper:** [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00946-z)
- **Upstream:** Hugging Face [`yangheng/PlantRNA-FM`](https://huggingface.co/yangheng/PlantRNA-FM)
- **License:** MIT (weights, per the Hugging Face model card); the image holds no PlantRNA-FM code.
- **Device:** CPU or GPU (images `rnazoo-plantrnafm-cpu` and `rnazoo-plantrnafm`).

## What it does

PlantRNA-FM is a 12-layer ESM-style transformer encoder (width 480, rotary positions, 33.8
million parameters). It was pretrained on protein-coding transcripts of 1,124 plant species (the
1KP dataset, about 25 million sequences) by masked nucleotide modeling plus prediction of
secondary structure and of UTR and CDS regions. The wrapper returns one 480-d embedding per
sequence (the mean over nucleotides) and optionally one per nucleotide.

## Input

FASTA. Letters are uppercased and T becomes U. Sequences over 1,024 nt are truncated with a
warning (1,026 tokens with the start and end tokens, the maximum the paper set for
fine-tuning); empty sequences are skipped.

Example (`tests/data/rnafm_test.fa`, used by the test profile; sequences shortened):

```
>test_rna_1
GGGUGCGAUCAUACCAGCACUAAUGCCCUCCUGG...
>test_rna_2
AUUCCGAGAGCUAACGGAGAACUCUGUUCGAUUU...
```

## Output

In `plantrnafm_out/`:

- `sequence_embeddings.npy`: shape `(N, 480)`, one row per sequence
- `labels.txt`: the FASTA headers, in row order
- with per-token output: `<header>_tokens.npy`, shape `(L, 480)`, for each sequence (spaces and
  `/` in the header become `_`)

Example, for the input above:

```python
import numpy as np
emb = np.load("plantrnafm_out/sequence_embeddings.npy")       # shape (2, 480)
names = open("plantrnafm_out/labels.txt").read().splitlines()  # ['test_rna_1', 'test_rna_2']
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-plantrnafm-cpu:latest \
  plantrnafm_predict.py -i /data/input.fa -o /out
```

For the GPU image, use `rnazoo-plantrnafm:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
Add `--per-token` for per-nucleotide embeddings.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --plantrnafm_input /path/to/input.fa
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/plantrnafm/plantrnafm_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--plantrnafm_input` | `null` | FASTA file |
| `--plantrnafm_per_token` | `false` | Also write per-nucleotide embeddings |
| `--plantrnafm_max_len` | `1024` | Truncate longer sequences to this many nt |
| `--plantrnafm_batch_size` | `8` | Sequences per forward pass; lower it if GPU memory runs out |

## Fine-tuning

Train a linear, MLP or XGBoost head on frozen PlantRNA-FM embeddings, as the [Fine Tuning
guide](../finetuning.md) describes. Its [common parameters](../finetuning.md#common-parameters)
take the prefix `plantrnafm`: `--plantrnafm_finetune_input` and `--plantrnafm_finetune_label`
are required, and `--plantrnafm_finetune_embeddings` reuses saved embeddings.

## Limitations

- Pretrained on plant transcripts only.
