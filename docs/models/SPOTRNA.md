# SPOT-RNA

Predict RNA secondary structure including pseudoknots and non-canonical base pairs.

- **Paper:** [Nature Communications 2019](https://doi.org/10.1038/s41467-019-13395-9)
- **Upstream:** https://github.com/jaswindersingh2/SPOT-RNA
- **License:** MPL-2.0
- **Device:** CPU or GPU (5-model TensorFlow ensemble). Two image variants:
    - `rnazoo-spotrna:latest` — CUDA-enabled (default, used with `-profile gpu`)
    - `rnazoo-spotrna-cpu:latest` — CPU-only (smaller, used with `-profile cpu`)

## What it does

SPOT-RNA predicts RNA secondary structure from sequence using an ensemble of 5 deep learning models. Unlike many structure prediction methods, it can predict:

- Canonical base pairs (AU, GC, GU)
- Non-canonical base pairs
- Pseudoknots
- All types of base pair interactions

The ensemble averages predictions across 5 models with different architectures for robust results.

## Input format

FASTA file of RNA sequences (A, C, G, U alphabet; T is auto-converted):

```
>2zzm_B
GGCAGAUCUGAGCCUGGGAGCUCUCUGCC
```

No hard length limit, but memory scales as O(L^2). Sequences under 500 nt are recommended for reasonable memory usage.

## Output format

**`structures.txt`** — FASTA-like file with dot-bracket notation (pseudoknot-aware):

```
>2zzm_B
GGCAGAUCUGAGCCUGGGAGCUCUCUGCC
((((((...(((((...).))))))))))
```

Per-sequence files:
- **`*.bpseq`** — base-pair format (index, base, pair partner; 0=unpaired)
- **`*.ct`** — connectivity table format
- **`*.prob`** — full L x L base-pair probability matrix

## Run with Docker

```bash
# CPU
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-spotrna-cpu:latest \
  spotrna_predict.py -i /data/input.fa -o /out

# GPU
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-spotrna:latest \
  spotrna_predict.py -i /data/input.fa -o /out
```

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu --spotrna_input /path/to/input.fa

# GPU
nextflow run main.nf -profile docker,gpu --spotrna_input /path/to/input.fa
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/spotrna/spotrna_out/`.

## Reading the probability matrix

```python
import numpy as np

# Load the full L x L pair probability matrix
prob = np.loadtxt("spotrna_out/2zzm_B.prob")
print(f"Shape: {prob.shape}")  # (29, 29)

# Find high-confidence pairs
pairs = np.argwhere(prob > 0.5)
print(f"Predicted pairs: {len(pairs)}")
```

## Example output

```
>2zzm_B
GGCAGAUCUGAGCCUGGGAGCUCUCUGCC
((((((...(((((...).))))))))))
```

This structure shows a stem-loop with nested base pairs and no pseudoknots for this particular sequence. When pseudoknots are present, they are denoted with `[]` and `{}` bracket types.

## Comparison with RNAformer

| Feature | SPOT-RNA | RNAformer |
|---------|----------|-----------|
| Framework | TensorFlow 2.x | PyTorch |
| Architecture | 5-model ensemble | Single model with recycling |
| Pseudoknots | Yes | Yes |
| Non-canonical pairs | Yes | Yes |
| Output formats | bpseq + ct + prob + dot-bracket | dot-bracket + optional prob matrix |
| Pretrained on | bpRNA + PDB + Rfam | bpRNA + PDB |
| License | MPL-2.0 | Apache 2.0 |

## Technical notes

- Uses TensorFlow 2.15 with `tf.compat.v1` (originally TF 1.14, updated for modern TF)
- 5 ensemble models range from 8-58 MB each (~155 MB total)
- Prediction threshold is hardcoded at 0.335
- Post-processing includes hairpin loop constraints, multiplet resolution, and lone pair removal
- The wrapper copies input FASTA to a temp file to avoid an upstream in-place overwrite bug
