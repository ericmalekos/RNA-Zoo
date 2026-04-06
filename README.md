# RiboZoo

A Nextflow pipeline that runs a "model zoo" of deep-learning models for riboseq / translation prediction.

## Models included

### Sequence → prediction

| Model | Task | Species | Paper | Upstream repo |
|---|---|---|---|---|
| RiboNN | sequence → TE per tissue/cell-type | human, mouse | [Nature Biotech 2025](https://www.nature.com/articles/s41587-025-02712-x) | [Sanofi-Public/RiboNN](https://github.com/Sanofi-Public/RiboNN) |
| seq2ribo | sequence → riboseq profile / TE / protein expr | human (4 cell lines) | [bioRxiv 2026](https://www.biorxiv.org/content/10.64898/2026.02.08.700508v1) | [Kingsford-Group/seq2ribo](https://github.com/Kingsford-Group/seq2ribo) |
| Saluki | sequence → mRNA half-life | human, mouse | [Genome Biology 2022](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-022-02811-x) | [calico/basenji](https://github.com/calico/basenji) |
| TranslationAI | sequence → TIS/TTS/ORFs | human | [NAR 2025](https://academic.oup.com/nar/article/53/7/gkaf277/8112693) | [rnasys/TranslationAI](https://github.com/rnasys/TranslationAI) |

### Codon design

| Model | Task | Species | Paper | Upstream repo |
|---|---|---|---|---|
| CodonTransformer | protein → optimized DNA codons | 164 organisms | [Nature Comms 2025](https://www.nature.com/articles/s41467-025-58588-7) | [Adibvafa/CodonTransformer](https://github.com/Adibvafa/CodonTransformer) |

### Ribo-seq refinement / correction

| Model | Task | Species | Paper | Upstream repo |
|---|---|---|---|---|
| Riboformer | refine codon-level ribosome density | E. coli, yeast, worm, SARS-CoV-2 | [Nature Comms 2024](https://www.nature.com/articles/s41467-024-46241-8) | [lingxusb/Riboformer](https://github.com/lingxusb/Riboformer) |
| RiboTIE | detect translated ORFs from ribo-seq + sequence | human, mouse | [Nature Comms 2025](https://www.nature.com/articles/s41467-025-56543-0) | [TRISTAN-ORF/TRISTAN](https://github.com/TRISTAN-ORF/TRISTAN) |

*(additional models coming)*

> **RiboTIE CPU warning:** RiboTIE fine-tunes the pretrained model on your ribo-seq data before predicting. This is fast on GPU (minutes) but slow on CPU for real-world datasets (hours+). Run with `-profile gpu` for realistic inputs, or use `-profile cpu` only for small tests.

> **seq2ribo GPU requirement:** seq2ribo requires an NVIDIA GPU with CUDA 11.8+ (uses Mamba SSM with custom CUDA kernels). It is automatically skipped under `-profile cpu`.
>
> **seq2ribo license:** CMU Academic/Non-Commercial Research Use Only. Commercial use is prohibited without permission from CMU. See the [seq2ribo LICENSE](https://github.com/Kingsford-Group/seq2ribo/blob/main/LICENSE).

## Quick start

```bash
# RiboNN: run with the bundled test input
nextflow run . -profile test,docker,cpu

# Riboformer: user provides a directory with WIG (fwd/rev), FASTA, and GFF3 files
nextflow run . -profile docker,cpu \
    --ignore_ribonn \
    --riboformer_input    /path/to/riboformer_dir \
    --riboformer_reference_wig GSM4127880_end3SM015Fd \
    --riboformer_target_wig    GSM4127896_SM015M \
    --riboformer_model    yeast_disome

# RiboTIE: user provides a directory with FASTA+GTF+BAMs plus a YAML config
nextflow run . -profile docker,cpu \
    --ignore_ribonn --ignore_riboformer \
    --ribotie_input  /path/to/ribotie_dir \
    --ribotie_config /path/to/config.yml

# Skip a specific model
nextflow run . -profile test,docker,cpu --ignore_ribonn
```

## Profiles

- `docker` / `singularity` — container engine
- `cpu` / `gpu` — hardware target (default: `gpu`, the model-native profile)
- `test` — bundled minimal inputs for smoke testing (RiboNN only; Riboformer skipped)

## Development

```bash
# Python linting
ruff check .

# Nextflow linting (requires nf-core tools)
nf-core lint
```
