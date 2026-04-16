# CodonTransformer

Optimize codon usage for protein sequences across 164 organisms.

- **Paper:** [Nature Communications 2025](https://www.nature.com/articles/s41467-025-58588-7)
- **Upstream:** https://github.com/Adibvafa/CodonTransformer
- **License:** Apache 2.0
- **Device:** CPU or GPU (model loading ~30s on CPU)

## What it does

CodonTransformer uses a BigBird transformer model to optimize codon usage for a given protein sequence and target organism. It takes amino acid sequences as input and outputs DNA coding sequences with optimized codons for expression in the target organism. Supports 164 organisms.

## Input format

FASTA file of amino acid sequences:

```
>test_protein_1
MALWMRLLPLLALLALWGPDPAAAFVN
>test_protein_2
MKWVTFISLLFLFSSAYS
```

## Output format

FASTA file of optimized DNA coding sequences (includes start and stop codons):

```
>test_protein_1
ATGGCCCTGTGGATGAGGCTGCTGCCCCTGCTGGCCCTGCTGGCCCTGTGGGGCCCTGACCCTGCTGCCGCCTTTGTGAACTGA
>test_protein_2
ATGAAGTGGGTGACCTTTATCTCTCTGCTGTTCCTGTTCTCTTCTGCCTACAGCTGA
```

## Run with Docker

```bash
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-codontransformer:latest \
  codon_transformer_predict.py \
    -i /data/input.fa \
    -o /out/optimized_codons.fa \
    --organism "Homo sapiens"
```

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --codontransformer_input /path/to/input.fa \
  --codontransformer_organism "Homo sapiens"
```

Only models with input provided will run — no ignore flags needed.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--codontransformer_organism` | `Homo sapiens` | Target organism (any of 164 supported organisms) |

## Supported organisms (partial list)

Homo sapiens, Mus musculus, Rattus norvegicus, Danio rerio, Drosophila melanogaster, Caenorhabditis elegans, Saccharomyces cerevisiae, Escherichia coli, Arabidopsis thaliana, and 155 more.

See the full list at https://github.com/Adibvafa/CodonTransformer.

## Example

**Input:**
```
>insulin_fragment
MALWMRLLPLLALLALWGPDPAAAFVN
```

**Output:**
```
>insulin_fragment
ATGGCCCTGTGGATGAGGCTGCTGCCCCTGCTGGCCCTGCTGGCCCTGTGGGGCCCTGACCCTGCTGCCGCCTTTGTGAACTGA
```

The optimized DNA sequence encodes the same protein but uses codons preferred by the target organism for improved expression.
