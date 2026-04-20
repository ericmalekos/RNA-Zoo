# MultiRM

Predict 12 RNA modification types from sequence.

- **Paper:** [NAR 2021](https://doi.org/10.1093/nar/gkab507)
- **Upstream:** https://github.com/Tsedao/MultiRM
- **License:** MIT
- **Device:** CPU or GPU (lightweight LSTM, ~8MB weights). Two image variants:
    - `rnazoo-multirm:latest` — CUDA-enabled (default, used with `-profile gpu`)
    - `rnazoo-multirm-cpu:latest` — CPU-only (smaller, used with `-profile cpu`)

## What it does

MultiRM is a multi-task deep learning model that simultaneously predicts 12 types of RNA modifications from sequence. It uses Word2Vec 3-mer embeddings, a bidirectional LSTM, and Bahdanau attention with 12 task-specific classification heads. For each position in the input sequence, it outputs a probability for each of the 12 modification types and a statistical significance (p-value) against a null distribution.

## The 12 modification types

| Code | Full Name |
|------|-----------|
| Am | 2'-O-methyladenosine |
| Cm | 2'-O-methylcytidine |
| Gm | 2'-O-methylguanosine |
| Um | 2'-O-methyluridine |
| m1A | N1-methyladenosine |
| m5C | 5-methylcytidine |
| m5U | 5-methyluridine |
| m6A | N6-methyladenosine |
| m6Am | N6,2'-O-dimethyladenosine |
| m7G | 7-methylguanosine |
| Psi | Pseudouridine |
| AtoI | Adenosine-to-inosine editing |

## Input format

FASTA file of RNA sequences (min 51 nt each). U is auto-converted to T internally.

```
>test_rna_modification
GGGGCCGTGGATACCTGCCTTTTAATTCTTTTTTATTCGCCCATCGGGGCCGCGGATACCTGCTTTTTATTTTTTTTTCCTTAGCCCATCGGGG
```

The first and last 25 nucleotides cannot be scored (edge padding for the 51-nt sliding window).

## Output format

**`modification_scores.tsv`** — per-position probabilities for all 12 modification types:

```
header	position	base	Am	Cm	Gm	Um	m1A	m5C	m5U	m6A	m6Am	m7G	Psi	AtoI
test_rna_modification	26	T	0.002129	0.000499	...	0.839820	...	0.017451
```

**`predicted_sites.tsv`** — only statistically significant predictions (p-value < alpha):

```
header	modification	position	base	probability	p_value
test_rna_modification	m6A	28	C	0.953859	0.000000
test_rna_modification	m6A	29	T	0.968842	0.000000
```

## Run with Docker

```bash
# CPU
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-multirm-cpu:latest \
  multirm_predict.py -i /data/input.fa -o /out

# GPU
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-multirm:latest \
  multirm_predict.py -i /data/input.fa -o /out
```

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu --multirm_input /path/to/input.fa

# GPU
nextflow run main.nf -profile docker,gpu --multirm_input /path/to/input.fa
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/multirm/multirm_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--multirm_alpha` | `0.05` | Significance threshold for calling modification sites |

## Technical notes

- Uses a 51-nt sliding window across the input. Each window is encoded as 49 overlapping 3-mers mapped to 300-d Word2Vec embeddings.
- The model is an LSTM + attention architecture (~8MB), making it one of the smallest models in the zoo.
- P-values are computed by comparing each prediction probability against a null distribution derived from negative samples.
- The wrapper re-implements the model architecture (CPU/GPU compatible) rather than using the upstream code which has hardcoded CUDA calls.
