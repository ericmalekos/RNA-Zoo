# RNAZoo

A Nextflow pipeline that runs a "model zoo" of deep-learning models for RNA sequence analysis — translation prediction, RNA structure, splicing, modifications, and more.

## Models included

### Translation / ribosome profiling

| Model | Task | Species | Paper | Upstream repo |
|---|---|---|---|---|
| RiboNN | sequence → TE per tissue/cell-type | human, mouse | [Nature Biotech 2025](https://www.nature.com/articles/s41587-025-02712-x) | [Sanofi-Public/RiboNN](https://github.com/Sanofi-Public/RiboNN) |
| seq2ribo | sequence → riboseq profile / TE / protein expr | human (4 cell lines) | [bioRxiv 2026](https://www.biorxiv.org/content/10.64898/2026.02.08.700508v1) | [Kingsford-Group/seq2ribo](https://github.com/Kingsford-Group/seq2ribo) |
| Saluki | sequence → mRNA half-life | human, mouse | [Genome Biology 2022](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-022-02811-x) | [calico/basenji](https://github.com/calico/basenji) |
| TranslationAI | sequence → TIS/TTS/ORFs | human | [NAR 2025](https://academic.oup.com/nar/article/53/7/gkaf277/8112693) | [rnasys/TranslationAI](https://github.com/rnasys/TranslationAI) |

### Ribo-seq refinement / correction

| Model | Task | Species | Paper | Upstream repo |
|---|---|---|---|---|
| Riboformer | refine codon-level ribosome density | E. coli, yeast, worm, SARS-CoV-2 | [Nature Comms 2024](https://www.nature.com/articles/s41467-024-46241-8) | [lingxusb/Riboformer](https://github.com/lingxusb/Riboformer) |
| RiboTIE | detect translated ORFs from ribo-seq + sequence | human, mouse | [Nature Comms 2025](https://www.nature.com/articles/s41467-025-56543-0) | [TRISTAN-ORF/TRISTAN](https://github.com/TRISTAN-ORF/TRISTAN) |

### Codon design

| Model | Task | Species | Paper | Upstream repo |
|---|---|---|---|---|
| CodonTransformer | protein → optimized DNA codons | 164 organisms | [Nature Comms 2025](https://www.nature.com/articles/s41467-025-58588-7) | [Adibvafa/CodonTransformer](https://github.com/Adibvafa/CodonTransformer) |

### Coming soon

RNA foundation models (RNA-FM, RiNALMo), RNA structure prediction (RNAformer, RhoFold, SPOT-RNA), splicing (SpliceAI, Pangolin, SpliceBERT), RNA modification (MultiRM), and mRNA design (UTR-LM, APARENT).

## Notices

> **seq2ribo GPU requirement:** seq2ribo requires an NVIDIA GPU with CUDA 11.8+ (uses Mamba SSM with custom CUDA kernels). It is automatically skipped under `-profile cpu`.

> **seq2ribo license:** CMU Academic/Non-Commercial Research Use Only. Commercial use is prohibited without permission from CMU. See the [seq2ribo LICENSE](https://github.com/Kingsford-Group/seq2ribo/blob/main/LICENSE).

> **TranslationAI license:** Source code is AGPL-3.0. Pretrained model weights are CC BY-NC 4.0 (non-commercial only).

> **RiboTIE CPU warning:** RiboTIE fine-tunes the pretrained model on your ribo-seq data before predicting. This is fast on GPU but slow on CPU for real-world datasets. Use `-profile gpu` for realistic inputs.

## Quick start

```bash
# Run the test profile (RiboNN on CPU)
nextflow run . -profile test,docker,cpu

# Skip a specific model
nextflow run . -profile test,docker,cpu --ignore_ribonn

# See all parameters
nextflow run . --help
```

## Profiles

- `docker` / `singularity` — container engine
- `cpu` / `gpu` — hardware target (default: `gpu`). GPU-only models auto-skip under `cpu`.
- `test` — bundled minimal inputs for smoke testing

## Development

```bash
# Python linting
ruff check .

# Nextflow linting (requires nf-core tools)
nf-core lint
```
