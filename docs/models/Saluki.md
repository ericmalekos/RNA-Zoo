# Saluki

Predict mRNA half-life from sequence.

- **Paper:** [Genome Biology 2022](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-022-02811-x)
- **Upstream:** https://github.com/calico/basenji (Saluki model)
- **License:** Apache 2.0 (weights from Zenodo)
- **Device:** CPU or GPU (CPU works but slower)

## What it does

Saluki predicts mRNA half-life from sequence using a convolutional neural network. It takes a single mRNA sequence (with UTR/CDS annotation via case convention) and outputs a log2(half-life) prediction. The model uses an ensemble of 50 cross-validated models (10 folds x 5 replicates) and supports both human and mouse.

## Input format

FASTA file where **lowercase = UTR** and **UPPERCASE = CDS**:

```
>test_transcript_1
gcgccgagcggcgccccgctgccctgtccccgcgtgcagaccccgggcccggccccggccATGCTGTGCGGCCGCTGG
AGGCGTTGCCGCCGCCCCGCCCGAGGAGCCCCCGGTGGCCGCCCAGGTCGCAGCCCAAGTCGCGGCGCCGGTCGCTCT
CCCGTCCCCGCCGACTCCCTCCGATGGCGGCACCAAGAGGCCCGGGCTGCGGGCGCTGAAGAAGATGGGCCTGACGGAG
...CACTCCAACAAcgaccgtctagagggggctgagatcgaggagttcctgcggcggctgctgaagcggccggag
```

- 5'UTR: lowercase at the start
- CDS: UPPERCASE in the middle
- 3'UTR: lowercase at the end

## Output format

NumPy file (`preds.npy`) containing an array of log2(mRNA half-life) predictions.

Shape: `(N, 1, 50)` where N = number of transcripts and 50 = ensemble members.

To read the output:

```python
import numpy as np
preds = np.load("preds.npy")
mean_pred = preds.mean(axis=-1)  # average across ensemble
print(f"Predicted log2(half-life): {mean_pred}")
```

## Run with Docker

```bash
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-saluki:latest \
  bash -c "saluki_predict_fasta.py -d 0 -o /out /opt/saluki_models /data/input.fa"
```

- `-d 0` = human, `-d 1` = mouse

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --saluki_input /path/to/input.fa \
  --saluki_species human
```

Only models with input provided will run — no ignore flags needed.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--saluki_species` | `human` | Species: `human` or `mouse` |

## Example output

For a single transcript, the 50-member ensemble produces:

```
Shape: (1, 1, 50)
Predictions (log2 half-life): [[[-0.695 -1.680 -1.501 -1.245 -1.145 -0.774 ... ]]]
```

The mean across the ensemble gives the final predicted log2(half-life). Negative values indicate short-lived transcripts; positive values indicate stable transcripts.
