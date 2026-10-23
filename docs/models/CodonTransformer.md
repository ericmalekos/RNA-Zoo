# CodonTransformer

Optimize codon usage for protein sequences across 164 organisms.

- **Paper:** [Nature Communications 2025](https://www.nature.com/articles/s41467-025-58588-7)
- **Upstream:** https://github.com/Adibvafa/CodonTransformer
- **License:** Apache 2.0
- **Device:** CPU or GPU (images `rnazoo-codontransformer-cpu` and `rnazoo-codontransformer`).

## What it does

A BigBird transformer writes a DNA coding sequence for each protein, with codons chosen for the
target organism. The base model was trained on about 1 million genes from 164 organisms; the
image holds the fine-tuned model (highly expressed genes of 13 organisms and two chloroplast
genomes).

## Input

FASTA of protein sequences; proteins over 2,046 amino acids are truncated without a warning. The
organism must be spelled as one of the 164 entries of `ORGANISM2ID` in upstream's
[`CodonUtils.py`](https://github.com/Adibvafa/CodonTransformer/blob/v1.6.7/CodonTransformer/CodonUtils.py),
for example `Homo sapiens`, `Mus musculus` or `Escherichia coli general`; other names stop the run.

```
>test_protein_1
MALWMRLLPLLALLALWGPDPAAAFVN
```

## Output

`optimized_codons.fa`: one DNA coding sequence per protein, under the same header, ending in a
stop codon. Example (`tests/data/codontransformer_test.fa`, `Homo sapiens`, test profile):

```
>test_protein_1
ATGGCCCTGTGGATGAGGCTGCTGCCCCTGCTGGCCCTGCTGGCCCTGTGGGGCCCTGACCCTGCTGCCGCCTTTGTGAACTGA
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-codontransformer-cpu:latest \
  codon_transformer_predict.py -i /data/input.fa -o /out/optimized_codons.fa --organism "Homo sapiens"
```

For the GPU image, use `rnazoo-codontransformer:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
Add `--no-deterministic` to sample codons.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --codontransformer_input /path/to/input.fa \
  --codontransformer_organism "Homo sapiens"
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/codontransformer/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--codontransformer_input` | `null` | Protein FASTA |
| `--codontransformer_organism` | `Homo sapiens` | Target organism, spelled as in upstream's list |
| `--codontransformer_deterministic` | `true` | `true` takes the most likely codons; `false` samples |

## Limitations

- A command-line `--codontransformer_deterministic false` can reach the module as the string
  `false`, which it treats as true. To sample, set `codontransformer_deterministic: false` in a
  `-params-file`.
