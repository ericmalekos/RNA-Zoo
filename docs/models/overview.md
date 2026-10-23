# Model Overview

RNA-Zoo runs 23 models in six tracks: 13 task programs and 10 embedding models. Each model runs
in its own container image, with its weights inside.

## All models at a glance

| Model | Track | Task | Input | Output | Device |
|-------|-------|------|-------|--------|--------|
| [RiboNN](RiboNN.md) | Translation | Translation efficiency in 78 human cell types | TSV of 5' UTR, CDS and 3' UTR sequences | TSV of TE per cell type | CPU or GPU |
| [Riboformer](Riboformer.md) | Translation | Codon-level ribosome density in a target condition | Directory of WIG, FASTA and GFF3 files | Density per codon window | CPU or GPU |
| [RiboTIE](RiboTIE.md) | Translation | Translated ORFs from ribosome profiling | Directory of FASTA, GTF and BAM files, plus a YAML config | ORFs as CSV and GTF per sample | CPU or GPU |
| [TranslationAI](TranslationAI.md) | Translation | Translation start and stop sites, and ORFs | FASTA of mRNAs | Text files of sites and ORFs | CPU |
| [Saluki](Saluki.md) | Translation | mRNA half-life score | FASTA (UTRs lowercase, CDS uppercase), optional exon lengths | TSV and NumPy array | CPU or GPU |
| [CodonTransformer](CodonTransformer.md) | Translation | Codon optimization for 164 organisms | FASTA of proteins | FASTA of DNA coding sequences | CPU or GPU |
| [RNA-FM](RNAFM.md) | Foundation | RNA embeddings, 640-d | FASTA | NumPy (N x 640) | CPU or GPU |
| [RiNALMo](RiNALMo.md) | Foundation | RNA embeddings, 1280-d | FASTA | NumPy (N x 1280) | CPU or GPU |
| [ERNIE-RNA](ERNIERNA.md) | Foundation | Structure-aware RNA embeddings, 768-d | FASTA | NumPy (N x 768) | CPU or GPU |
| [Orthrus](Orthrus.md) | Foundation | Mature mRNA embeddings, 512-d (256-d for two of the seven checkpoints) | FASTA of mature mRNAs | NumPy (N x D) | GPU only |
| [HydraRNA](HydraRNA.md) | Foundation | Full-length RNA embeddings, 1024-d | FASTA | NumPy (N x 1024) | GPU only |
| [RNAErnie](RNAErnie.md) | Foundation | RNA embeddings, 768-d | FASTA | NumPy (N x 768) | CPU or GPU |
| [PlantRNA-FM](PlantRNAFM.md) | Foundation | Plant RNA embeddings, 480-d | FASTA | NumPy (N x 480) | CPU or GPU |
| [CaLM](CaLM.md) | Foundation | Codon-level embeddings of coding sequences, 768-d | FASTA of in-frame coding sequences | NumPy (N x 768) | CPU or GPU |
| [mRNABERT](mRNABERT.md) | Foundation | mRNA embeddings, 768-d | FASTA of mRNAs | NumPy (N x 768) | CPU or GPU |
| [RhoFold](RhoFold.md) | Structure | 3D structure from a single sequence | FASTA | PDB, CT and NPZ per sequence | CPU or GPU |
| [SPOT-RNA](SPOTRNA.md) | Structure | Secondary structure with pseudoknots | FASTA | Dot-bracket, bpseq, CT and pair probabilities | CPU or GPU |
| [DRfold2](DRfold2.md) | Structure | 3D structure from a single sequence | FASTA | PDB per sequence | GPU only |
| [Pangolin](Pangolin.md) | Splicing | Variant effects on splice-site strength, from models of four tissues | VCF or CSV, reference FASTA, gffutils database | VCF or CSV with scores | CPU or GPU |
| [SpliceAI](SpliceAI.md) | Splicing | Variant effects on splicing | VCF, reference FASTA, gene annotation | VCF with four delta scores | CPU or GPU |
| [SpliceBERT](SpliceBERT.md) | Splicing | Primary RNA (pre-mRNA) embeddings, 512-d | FASTA | NumPy (N x 512) | CPU or GPU |
| [MultiRM](MultiRM.md) | Modification | Sites of 12 RNA modification types | FASTA (at least 51 nt) | TSV of probabilities and p-values | CPU or GPU |
| [UTR-LM](UTRLM.md) | mRNA Design | Mean ribosome loading, translation efficiency or expression level | FASTA of 5' UTRs | TSV | CPU or GPU |

## By track

### Translation

RiboNN, TranslationAI, Saluki and CodonTransformer need only sequences. Riboformer and RiboTIE
also need ribosome profiling data: Riboformer predicts the density in a target condition from a
reference dataset, and RiboTIE fine-tunes on each sample's reads before it calls ORFs.

### RNA foundation models

The nine foundation models and SpliceBERT (splicing track) return embeddings: one vector per
sequence in `sequence_embeddings.npy`, the names in `labels.txt`, and one vector per token with
`--<model>_per_token`. They differ in size, pretraining data and input limit:

| Model | Parameters | Width | Pretraining data | Max input |
|-------|-----------:|------:|------------------|-----------|
| [RNA-FM](RNAFM.md) | 99.5M | 640 | 23M non-coding RNAs (RNAcentral) | 1,022 nt |
| [RiNALMo](RiNALMo.md) | 650.9M | 1280 | 36M non-coding RNAs (RNAcentral and other databases) | No cap; memory-bound |
| [ERNIE-RNA](ERNIERNA.md) | 86.3M | 768 | 20.4M non-coding RNAs (RNAcentral) | 1,022 nt |
| [Orthrus](Orthrus.md) | 10.2M (default checkpoint) | 512 (256 for two checkpoints) | Splice isoforms of ten metazoans and orthologs from over 400 mammals, by contrastive learning | No cap |
| [HydraRNA](HydraRNA.md) | 84.2M | 1024 | 28M non-coding RNAs and mRNAs | No cap; 10,240-nt chunks, averaged |
| [RNAErnie](RNAErnie.md) | 86.6M | 768 | About 31M RNAcentral sequences (a later PyTorch model by the authors, not the paper's) | 2,046 nt |
| [PlantRNA-FM](PlantRNAFM.md) | 33.8M | 480 | Transcripts of 1,124 plant species (about 25M sequences) | 1,024 nt |
| [CaLM](CaLM.md) | 85.7M | 768 | 9M coding sequences (European Nucleotide Archive) | 1,024 codons |
| [mRNABERT](mRNABERT.md) | 113.4M | 768 | About 18M mRNAs | 1,022 tokens (UTR nucleotides and CDS codons) |
| [SpliceBERT](SpliceBERT.md) | 19.4M | 512 | Over 2M primary RNAs from 72 vertebrates | 1,024 nt |

Inputs over the limit are truncated with a warning. The sequence embedding is the mean over
positions, without the start and end tokens; ERNIE-RNA instead returns its CLS token.

### RNA structure

RhoFold and DRfold2 predict 3D structure from a single sequence. RhoFold takes up to 1,022 nt
and runs on CPU or GPU; DRfold2 has no length cap but needs a GPU. SPOT-RNA predicts secondary
structure, including pseudoknots and non-canonical pairs.

### Splicing

SpliceAI and Pangolin score variants against a reference genome and a gene annotation.
SpliceBERT only returns embeddings.

## Fine-tuning

The nine foundation models can train a linear, MLP or XGBoost head on their frozen embeddings
and your labels; see the [Fine Tuning guide](../finetuning.md). SpliceBERT has no fine-tuning
parameters. RiboTIE fine-tunes its pretrained models on each sample's reads in every run.
[RiboNN](RiboNN.md#fine-tuning-on-your-own-data) and
[UTR-LM](UTRLM.md#fine-tuning-on-your-own-data) have their own fine-tuning modules, but both
currently fail and are not tested; a fix is planned for a later release.

## Licenses

| Model | License | Upstream | Paper |
|-------|---------|--------|-------|
| RiboNN | Sanofi academic, non-commercial license (code and weights); image redistributed with the authors' permission | [Sanofi-Public/RiboNN](https://github.com/Sanofi-Public/RiboNN) | [Nature Biotechnology 2025](https://www.nature.com/articles/s41587-025-02712-x) |
| Riboformer | MIT (code and weights) | [lingxusb/Riboformer](https://github.com/lingxusb/Riboformer) | [Nature Communications 2024](https://www.nature.com/articles/s41467-024-46241-8) |
| RiboTIE | MIT (code and weights) | [TRISTAN-ORF/TRISTAN](https://github.com/TRISTAN-ORF/TRISTAN) | [Nature Communications 2025](https://www.nature.com/articles/s41467-025-56543-0) |
| TranslationAI | AGPL-3.0 (code); CC BY-NC 4.0 (weights) | [rnasys/TranslationAI](https://github.com/rnasys/TranslationAI) | [NAR 2025](https://academic.oup.com/nar/article/53/7/gkaf277/8112693) |
| Saluki | Apache-2.0 (code); CC BY 4.0 (weights) | [calico/basenji](https://github.com/calico/basenji) | [Genome Biology 2022](https://genomebiology.biomedcentral.com/articles/10.1186/s13059-022-02811-x) |
| CodonTransformer | Apache-2.0 (code and weights) | [Adibvafa/CodonTransformer](https://github.com/Adibvafa/CodonTransformer) | [Nature Communications 2025](https://www.nature.com/articles/s41467-025-58588-7) |
| RNA-FM | MIT (code); Apache-2.0 (weights) | [ml4bio/RNA-FM](https://github.com/ml4bio/RNA-FM) | [arXiv 2022](https://arxiv.org/abs/2204.00300) |
| RiNALMo | Apache-2.0 (code); CC BY 4.0 (weights) | [lbcb-sci/RiNALMo](https://github.com/lbcb-sci/RiNALMo) | [Nature Communications 2025](https://www.nature.com/articles/s41467-025-60872-5) |
| ERNIE-RNA | MIT (code); no license stated for the weights | [Bruce-ywj/ERNIE-RNA](https://github.com/Bruce-ywj/ERNIE-RNA) | [Nature Communications 2025](https://www.nature.com/articles/s41467-025-64972-0) |
| Orthrus | MIT (code and weights) | [bowang-lab/Orthrus](https://github.com/bowang-lab/Orthrus) | [Nature Methods 2026](https://www.nature.com/articles/s41592-026-03064-3) |
| HydraRNA | MIT (code and weights) | [GuipengLi/HydraRNA](https://github.com/GuipengLi/HydraRNA) | [Genome Biology 2025](https://doi.org/10.1186/s13059-025-03853-7) |
| RNAErnie | Apache-2.0 (the `LLM-EDA/RNAErnie` weights the image loads); MIT (the original PaddlePaddle code, not in the image) | [CatIIIIIIII/RNAErnie](https://github.com/CatIIIIIIII/RNAErnie) | [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00836-4) |
| PlantRNA-FM | MIT (weights; the image holds no PlantRNA-FM code) | [yangheng/PlantRNA-FM](https://huggingface.co/yangheng/PlantRNA-FM) | [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00946-z) |
| CaLM | BSD-3-Clause (code); no license stated for the weights | [oxpig/CaLM](https://github.com/oxpig/CaLM) | [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00791-0) |
| mRNABERT | Apache-2.0 (code and weights) | [yyly6/mRNABERT](https://github.com/yyly6/mRNABERT) | [Nature Communications 2025](https://doi.org/10.1038/s41467-025-65340-8) |
| RhoFold | Apache-2.0 (code and weights) | [ml4bio/RhoFold](https://github.com/ml4bio/RhoFold) | [Nature Methods 2024](https://doi.org/10.1038/s41592-024-02487-0) |
| SPOT-RNA | MPL-2.0 (code); no license stated for the weights | [jaswindersingh2/SPOT-RNA](https://github.com/jaswindersingh2/SPOT-RNA) | [Nature Communications 2019](https://doi.org/10.1038/s41467-019-13395-9) |
| DRfold2 | MIT, stated in the README (no LICENSE file); no license stated for the weights; the bundled Arena declares no license; image redistributed with the authors' permission | [leeyang/DRfold2](https://github.com/leeyang/DRfold2) | [PLOS Biology 2026](https://doi.org/10.1371/journal.pbio.3003659) |
| MultiRM | MIT (code and weights) | [Tsedao/MultiRM](https://github.com/Tsedao/MultiRM) | [Nature Communications 2021](https://doi.org/10.1038/s41467-021-24313-3) |
| Pangolin | GPL-3.0 (code and models) | [tkzeng/Pangolin](https://github.com/tkzeng/Pangolin) | [Genome Biology 2022](https://doi.org/10.1186/s13059-022-02664-4) |
| SpliceAI | Installed release 1.3.1: GPL-3.0-or-later (code), no license stated for the weights. Later upstream releases: PolyForm Strict 1.0.0 (code), CC BY-NC 4.0 (weights). Image redistributed with the authors' permission | [Illumina/SpliceAI](https://github.com/Illumina/SpliceAI) | [Cell 2019](https://doi.org/10.1016/j.cell.2018.12.015) |
| SpliceBERT | BSD-3-Clause (code); CC BY 4.0 (weights) | [biomed-AI/SpliceBERT](https://github.com/biomed-AI/SpliceBERT) | [Briefings in Bioinformatics 2024](https://doi.org/10.1093/bib/bbae163) |
| UTR-LM | GPL-3.0 (code and weights) | [a96123155/UTR-LM](https://github.com/a96123155/UTR-LM) | [Nature Machine Intelligence 2024](https://doi.org/10.1038/s42256-024-00823-9) |
