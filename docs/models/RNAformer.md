# RNAformer

Predict RNA secondary structure (base-pair matrix) from sequence.

- **Paper:** [ICLR 2024](https://openreview.net/forum?id=RNAformer)
- **Upstream:** https://github.com/automl/RNAformer
- **License:** Apache 2.0
- **Device:** CPU or GPU (32M params, runs well on CPU)

## What it does

RNAformer is a transformer model that predicts RNA secondary structure from sequence. It outputs a base-pair probability matrix (L x L), from which base pairs and dot-bracket notation are derived. The model uses axial attention over 2D latent representations and supports recycling for iterative refinement.

The default checkpoint (`intra_family_finetuned`) is fine-tuned with LoRA on experimentally determined PDB structures, giving the best general-purpose accuracy.

## Input format

FASTA file of RNA sequences (A, C, G, U alphabet; T is auto-converted to U).

**Maximum sequence length: ~500 nt** for the finetuned checkpoints (rotary position embeddings, flexible but memory scales quadratically).

Example (`tests/data/rnaformer_test.fa`):

```
>tRNA_Phe
GCCCGCAUGGUGAAAUCGGUAAACACAUCGCACUAAUGCGCCGCCUCUGGCUUGCCGGUUCAAGUCCGGCUGCGGGCACCA
>5S_rRNA_fragment
GCCUGGCGGCCGUAGCGCGGUGGUCCCACCUGACCCCAUGCCGAACUCAGAAGUGAAACGCCGUAGCGCCGAUGGUAG
```

## Output format

**`structures.txt`**: FASTA-like file with three lines per sequence (header, sequence, dot-bracket structure):

```
>tRNA_Phe
GCCCGCAUGGUGAAAUCGGUAAACACAUCGCACUAAUGCGCCGCCUCUGGCUUGCCGGUUCAAGUCCGGCUGCGGGCACCA
(((((((([{{[[(.......)]]}}...((........)).(((...)))..((((((...)..))))))))))))....
```

Dot-bracket notation: `()`=nested pairs, `[]`=first pseudoknot level, `{}`=second pseudoknot level, `.`=unpaired.

With `--save-matrix`: also saves per-sequence base-pair probability matrices as `<name>_bpmat.npy` (NumPy array, shape L x L, values 0-1).

## Run with Docker

```bash
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rnaformer:latest \
  rnaformer_predict.py -i /data/input.fa -o /out
```

With probability matrices:

```bash
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-rnaformer:latest \
  rnaformer_predict.py -i /data/input.fa -o /out --save-matrix
```

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --rnaformer_input /path/to/input.fa
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/rnaformer/rnaformer_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--rnaformer_cycling` | `6` | Number of recycling steps (6=best quality, 0=disable) |
| `--rnaformer_save_matrix` | `false` | Also save L x L base-pair probability matrices as .npy |

## Reading the probability matrix

```python
import numpy as np

# Load the base-pair probability matrix
bpmat = np.load("rnaformer_out/tRNA_Phe_bpmat.npy")  # (81, 81)
print(f"Shape: {bpmat.shape}")
print(f"Max probability: {bpmat.max():.3f}")

# Threshold to get binary pairs
pairs = np.argwhere(bpmat > 0.5)
print(f"Number of predicted base pairs: {len(pairs) // 2}")
```

## Example output

```
>tRNA_Phe
GCCCGCAUGGUGAAAUCGGUAAACACAUCGCACUAAUGCGCCGCCUCUGGCUUGCCGGUUCAAGUCCGGCUGCGGGCACCA
(((((((([{{[[(.......)]]}}...((........)).(((...)))..((((((...)..))))))))))))....
>5S_rRNA_fragment
GCCUGGCGGCCGUAGCGCGGUGGUCCCACCUGACCCCAUGCCGAACUCAGAAGUGAAACGCCGUAGCGCCGAUGGUAG
(((...(((.....((((((((((.(([[((((.[(([[...(])))]))())[(]))))))))[)].)))..))).
```

## Available checkpoints

The Docker image bundles the `intra_family_finetuned` checkpoint (default, best for general use). Other checkpoints can be downloaded from the upstream server:

| Checkpoint | Description | Trained on |
|-----------|-------------|------------|
| `intra_family_finetuned` | **Default.** LoRA-finetuned on PDB structures | PDB (intra-family split) |
| `inter_family_finetuned` | LoRA-finetuned on PDB structures | PDB (inter-family split) |
| `bprna` | Base model | bpRNA dataset |
| `biophysical` | Base model | Synthetic biophysical data |
