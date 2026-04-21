# Model Overview

RNAZoo includes 15 RNA deep learning models across 5 tracks. Each model runs in its own Docker container with baked-in weights.

## All models at a glance

| Model | Track | Task | Input | Output | Device | License |
|-------|-------|------|-------|--------|--------|---------|
| [RiboNN](RiboNN.md) | Translation | TE prediction (82 cell types) | Tab-separated (UTR+CDS) | TSV with TE per cell type | CPU/GPU | Apache 2.0 |
| [Riboformer](Riboformer.md) | Translation | Codon-level ribosome density | WIG + FASTA + GFF3 | Density predictions | CPU/GPU | Upstream |
| [RiboTIE](RiboTIE.md) | Translation | ORF detection from ribo-seq | FASTA + GTF + BAM | GTF + CSV | CPU/GPU | Upstream |
| [seq2ribo](seq2ribo.md) | Translation | Riboseq/TE/protein from sequence | FASTA (CDS) | JSON | **GPU only** | CMU Non-Commercial |
| [TranslationAI](TranslationAI.md) | Translation | TIS/TTS/ORF prediction | FASTA (mRNA) | TIS/TTS/ORF text files | CPU/GPU | AGPL-3.0 + CC BY-NC 4.0 |
| [Saluki](Saluki.md) | Translation | mRNA half-life | FASTA (case=UTR/CDS) | NumPy array | CPU/GPU | Apache 2.0 |
| [CodonTransformer](CodonTransformer.md) | Translation | Codon optimization | FASTA (protein) | FASTA (DNA) | CPU/GPU | Apache 2.0 |
| [RNA-FM](RNAFM.md) | Foundation | RNA embeddings (640-d) | FASTA (RNA) | NumPy (N x 640) | CPU/GPU | MIT |
| [RiNALMo](RiNALMo.md) | Foundation | RNA embeddings (1280-d) | FASTA (RNA) | NumPy (N x 1280) | CPU/GPU | Apache 2.0 |
| [ERNIE-RNA](ERNIERNA.md) | Foundation | Structure-aware embeddings (768-d) | FASTA (RNA) | NumPy (N x 768) | CPU/GPU | MIT |
| [RNAformer](RNAformer.md) | Structure | 2D structure (base-pair matrix) | FASTA (RNA) | Dot-bracket + prob matrix | CPU/GPU | Apache 2.0 |
| [RhoFold](RhoFold.md) | Structure | 3D structure prediction | FASTA (RNA) | PDB + CT | CPU/GPU | Apache 2.0 |
| [SPOT-RNA](SPOTRNA.md) | Structure | 2D structure + pseudoknots | FASTA (RNA) | bpseq + CT + prob + dot-bracket | CPU/GPU | MPL-2.0 |
| [MultiRM](MultiRM.md) | Modification | 12 RNA modification types | FASTA (RNA, min 51 nt) | TSV (probabilities + p-values) | CPU/GPU | MIT |
| [UTR-LM](UTRLM.md) | mRNA Design | MRL / TE / expression level | FASTA (5'UTR DNA) | TSV (predictions) | CPU/GPU | GPL-3.0 |

## By track

### Translation (7 models)

Models for predicting translation efficiency, ribosome profiling, ORF detection, mRNA stability, and codon optimization.

- **[RiboNN](RiboNN.md)** — Multi-task TE prediction across 82 human cell types from mRNA sequence
- **[Riboformer](Riboformer.md)** — Refine codon-level ribosome densities from ribo-seq data
- **[RiboTIE](RiboTIE.md)** — Detect translated ORFs from ribo-seq + genomic sequence
- **[seq2ribo](seq2ribo.md)** — Predict ribosome profiles/TE/protein from mRNA sequence (GPU only)
- **[TranslationAI](TranslationAI.md)** — Identify translation initiation/termination sites and ORFs
- **[Saluki](Saluki.md)** — Predict mRNA half-life from sequence (50-model ensemble)
- **[CodonTransformer](CodonTransformer.md)** — Optimize codon usage for 164 organisms

### RNA Foundation Models (3 models)

General-purpose RNA language models that produce embeddings for downstream tasks.

- **[RNA-FM](RNAFM.md)** — 99M params, 640-d embeddings, max 1022 nt (MIT)
- **[RiNALMo](RiNALMo.md)** — 650M params, 1280-d embeddings, no hard length limit (Apache 2.0)
- **[ERNIE-RNA](ERNIERNA.md)** — 86M params, 768-d embeddings, structure-aware attention (MIT)

### RNA Structure (3 models)

Secondary and 3D structure prediction from sequence.

- **[RNAformer](RNAformer.md)** — 2D base-pair matrix with recycling, pseudoknot-aware
- **[RhoFold](RhoFold.md)** — Full-atom 3D structure prediction (PDB output), single-sequence mode
- **[SPOT-RNA](SPOTRNA.md)** — 2D structure with pseudoknots, 5-model TF ensemble

### RNA Modification (1 model)

- **[MultiRM](MultiRM.md)** — Predicts 12 RNA modification types per position (m6A, m5C, pseudouridine, Am, Cm, Gm, Um, m1A, m5U, m6Am, m7G, A-to-I editing)

### mRNA Design (1 model)

- **[UTR-LM](UTRLM.md)** — Predicts mean ribosome loading, translation efficiency, or expression level from 5'UTR sequences

## Fine-tuning support

Some models can be fine-tuned on your own data. Fine-tuned checkpoints are saved to disk and can be reused for subsequent predictions.

| Model | Fine-tuning | Details |
|-------|-------------|---------|
| [RiboNN](RiboNN.md#fine-tuning-on-your-own-data) | Transfer learning | Freeze pretrained conv layers, train head on user TE data; use saved checkpoint via `--ribonn_checkpoint` |
| [UTR-LM](UTRLM.md#fine-tuning-on-your-own-data) | Full fine-tuning | Train ESM2 backbone + head on user MRL/TE/EL data; use saved checkpoint for prediction |
| [RiboTIE](RiboTIE.md) | Built-in | Automatically fine-tunes on user ribo-seq BAMs before ORF prediction |

## Licenses

| Model | License | GitHub | Paper |
|-------|---------|--------|-------|
| RiboNN | Apache 2.0 | [Sanofi-Public/RiboNN](https://github.com/Sanofi-Public/RiboNN) | [Nature Biotechnology 2025](https://www.nature.com/articles/s41587-025-02712-x) |
| Riboformer | MIT | [lingxusb/Riboformer](https://github.com/lingxusb/Riboformer) | [Nature Communications 2024](https://www.nature.com/articles/s41467-024-46241-8) |
| RiboTIE | MIT | [TRISTAN-ORF/TRISTAN](https://github.com/TRISTAN-ORF/TRISTAN) | [Nature Communications 2025](https://www.nature.com/articles/s41467-025-56543-0) |
| seq2ribo | CMU Non-Commercial | [Kingsford-Group/seq2ribo](https://github.com/Kingsford-Group/seq2ribo) | [bioRxiv 2026](https://www.biorxiv.org/content/10.64898/2026.02.08.700508v1) |
| TranslationAI | AGPL-3.0 + CC BY-NC 4.0 | [rnasys/TranslationAI](https://github.com/rnasys/TranslationAI) | [NAR 2025](https://academic.oup.com/nar/article/53/7/gkaf277/8112693) |
| Saluki | Apache 2.0 | [calico/basenji](https://github.com/calico/basenji) | [Genome Biology 2022](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-022-02811-x) |
| CodonTransformer | Apache 2.0 | [Adibvafa/CodonTransformer](https://github.com/Adibvafa/CodonTransformer) | [Nature Communications 2025](https://www.nature.com/articles/s41467-025-58588-7) |
| RNA-FM | MIT | [ml4bio/RNA-FM](https://github.com/ml4bio/RNA-FM) | [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00836-4) |
| RiNALMo | Apache 2.0 (code) + CC BY 4.0 (weights) | [lbcb-sci/RiNALMo](https://github.com/lbcb-sci/RiNALMo) | [NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/RiNALMo) |
| ERNIE-RNA | MIT | [Bruce-ywj/ERNIE-RNA](https://github.com/Bruce-ywj/ERNIE-RNA) | [Nature Communications 2025](https://www.nature.com/articles/s41467-025-64972-0) |
| RNAformer | Apache 2.0 | [automl/RNAformer](https://github.com/automl/RNAformer) | [ICLR 2024](https://openreview.net/forum?id=RNAformer) |
| RhoFold | Apache 2.0 | [ml4bio/RhoFold](https://github.com/ml4bio/RhoFold) | [Nature Methods 2024](https://doi.org/10.1038/s41592-024-02487-0) |
| SPOT-RNA | MPL-2.0 | [jaswindersingh2/SPOT-RNA](https://github.com/jaswindersingh2/SPOT-RNA) | [Nature Communications 2019](https://doi.org/10.1038/s41467-019-13395-9) |
| MultiRM | MIT | [Tsedao/MultiRM](https://github.com/Tsedao/MultiRM) | [NAR 2021](https://doi.org/10.1093/nar/gkab507) |
| UTR-LM | GPL-3.0 | [a96123155/UTR-LM](https://github.com/a96123155/UTR-LM) | [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00823-9) |
