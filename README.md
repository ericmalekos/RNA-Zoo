# RNAZoo

[![CI (Lint)](https://github.com/ericmalekos/RNA-Zoo/actions/workflows/ci.yml/badge.svg)](https://github.com/ericmalekos/RNA-Zoo/actions/workflows/ci.yml)
[![CI (Pipeline)](https://github.com/ericmalekos/RNA-Zoo/actions/workflows/ci-pipeline.yml/badge.svg)](https://github.com/ericmalekos/RNA-Zoo/actions/workflows/ci-pipeline.yml)
[![CI (Singularity)](https://github.com/ericmalekos/RNA-Zoo/actions/workflows/ci-singularity.yml/badge.svg)](https://github.com/ericmalekos/RNA-Zoo/actions/workflows/ci-singularity.yml)
[![Lint](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Documentation](https://img.shields.io/badge/docs-ericmalekos.github.io%2FRNA--Zoo-blue)](https://ericmalekos.github.io/RNA-Zoo)

A Nextflow pipeline model zoo for RNA deep learning — 22 models across translation, structure, modification, and more.

| Model | Track | Task | Paper | License |
|-------|-------|------|-------|---------|
| [RiboNN](https://github.com/Sanofi-Public/RiboNN) | Translation | TE prediction (82 cell types) | [Nature Biotech 2025](https://www.nature.com/articles/s41587-025-02712-x) | Apache 2.0 |
| [Riboformer](https://github.com/lingxusb/Riboformer) | Translation | Codon-level ribosome density | [Nature Comms 2024](https://www.nature.com/articles/s41467-024-46241-8) | MIT |
| [RiboTIE](https://github.com/TRISTAN-ORF/TRISTAN) | Translation | ORF detection from ribo-seq | [Nature Comms 2025](https://www.nature.com/articles/s41467-025-56543-0) | MIT |
| [seq2ribo](https://github.com/Kingsford-Group/seq2ribo) | Translation | Riboseq / TE / protein (GPU) | [bioRxiv 2026](https://www.biorxiv.org/content/10.64898/2026.02.08.700508v1) | CMU Non-Commercial |
| [TranslationAI](https://github.com/rnasys/TranslationAI) | Translation | TIS / TTS / ORF prediction | [NAR 2025](https://academic.oup.com/nar/article/53/7/gkaf277/8112693) | AGPL-3.0 + CC BY-NC 4.0 |
| [Saluki](https://github.com/calico/basenji) | Translation | mRNA half-life | [Genome Biology 2022](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-022-02811-x) | Apache 2.0 |
| [CodonTransformer](https://github.com/Adibvafa/CodonTransformer) | Translation | Codon optimization (164 organisms) | [Nature Comms 2025](https://www.nature.com/articles/s41467-025-58588-7) | Apache 2.0 |
| [RNA-FM](https://github.com/ml4bio/RNA-FM) | Foundation | RNA embeddings (640-d) | [arXiv 2022](https://arxiv.org/abs/2204.00300) | MIT |
| [RiNALMo](https://github.com/lbcb-sci/RiNALMo) | Foundation | RNA embeddings (1280-d) | [NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/RiNALMo) | Apache 2.0 |
| [ERNIE-RNA](https://github.com/Bruce-ywj/ERNIE-RNA) | Foundation | Structure-aware embeddings (768-d) | [Nature Comms 2025](https://www.nature.com/articles/s41467-025-64972-0) | MIT |
| [Orthrus](https://github.com/bowang-lab/Orthrus) | Foundation | Mamba mRNA embeddings (4-track, 512-d, GPU) | [Nature Methods 2026](https://www.nature.com/articles/s41592-026-03064-3) | MIT |
| [RNAErnie](https://github.com/CatIIIIIIII/RNAErnie) | Foundation | Motif-aware RNA embeddings (768-d) | [Nature Mach Intell 2024](https://doi.org/10.1038/s42256-024-00836-4) | Apache-2.0 |
| [PlantRNA-FM](https://huggingface.co/yangheng/PlantRNA-FM) | Foundation | Plant-only RNA embeddings (480-d) | [Nature Mach Intell 2024](https://doi.org/10.1038/s42256-024-00946-z) | MIT |
| [CaLM](https://github.com/oxpig/CaLM) | Foundation | Codon-level RNA embeddings (768-d) | [Nature Mach Intell 2024](https://doi.org/10.1038/s42256-024-00791-0) | BSD-3-Clause |
| [mRNABERT](https://huggingface.co/YYLY66/mRNABERT) | Foundation | Hybrid UTR/CDS mRNA embeddings (768-d) | [Nature Comms 2025](https://doi.org/10.1038/s41467-025-65340-8) | Apache-2.0 |
| [HydraRNA](https://github.com/GuipengLi/HydraRNA) | Foundation | Hybrid Mamba+attention RNA embeddings (1024-d, ≤10K nt, GPU) | [Genome Biology 2025](https://doi.org/10.1186/s13059-025-03853-7) | MIT |
| [RNAformer](https://github.com/automl/RNAformer) | Structure | 2D base-pair prediction | [ICLR 2024](https://openreview.net/forum?id=RNAformer) | Apache 2.0 |
| [RhoFold](https://github.com/ml4bio/RhoFold) | Structure | 3D structure (PDB output) | [Nature Methods 2024](https://doi.org/10.1038/s41592-024-02487-0) | Apache 2.0 |
| [SPOT-RNA](https://github.com/jaswindersingh2/SPOT-RNA) | Structure | 2D structure + pseudoknots | [Nature Comms 2019](https://doi.org/10.1038/s41467-019-13395-9) | MPL-2.0 |
| [DRfold2](https://github.com/leeyang/DRfold2) | Structure | Single-seq ab initio 3D (GPU) | [Li et al. 2025](https://github.com/leeyang/DRfold2) | MIT |
| [MultiRM](https://github.com/Tsedao/MultiRM) | Modification | 12 RNA modification types | [NAR 2021](https://doi.org/10.1093/nar/gkab507) | MIT |
| [UTR-LM](https://github.com/a96123155/UTR-LM) | mRNA Design | 5'UTR MRL / TE / expression | [Nature Mach Intell 2024](https://doi.org/10.1038/s42256-024-00823-9) | GPL-3.0 |
