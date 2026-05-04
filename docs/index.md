# RNAZoo

**A Nextflow pipeline model zoo for RNA deep learning.**

## What's included

25 models across 6 tracks. Every container has its model weights baked in at build time — no runtime downloads. Image sizes below are the **compressed download size** from GHCR; on disk they roughly double after extraction.

### RNA Foundation Models

All foundation models take a FASTA of RNA sequences and write `sequence_embeddings.npy` (shape `(N, D)`) plus a matching `labels.txt`. Per-token `(L, D)` embeddings are available with `--<model>_per_token`.

| Model | Architecture | Output dim | Pooling | Training set | Max input | GPU image | CPU image |
|-------|--------------|-----------|---------|--------------|-----------|-----------|-----------|
| [RNA-FM](models/RNAFM.md) | 12-layer Transformer | **640-d** | Mean (excl CLS+EOS) | 23M ncRNAs (RNAcentral) | 1022 nt | 4.2 GB | 1.7 GB |
| [RiNALMo](models/RiNALMo.md) | 33-layer Transformer (650M params) | **1280-d** | Mean (excl CLS+EOS) | 36M ncRNAs (RNAcentral) | ~11k nt (memory-bound) | 5.6 GB | 3.1 GB |
| [ERNIE-RNA](models/ERNIERNA.md) | 12-layer Transformer + 2D structure attention | **768-d** | **[CLS]** | 20M ncRNAs (RNAcentral) | 1022 nt | 5.7 GB | — (single image) |
| [Orthrus](models/Orthrus.md) | 6-layer Mamba SSM (~10M params) | **512-d** | Mean (`mean_unpadded`) | 32.7M mRNAs (GENCODE+RefSeq+Zoonomia, contrastive) | unbounded (linear mem) | ~5 GB | — (GPU only) |
| [RNAErnie](models/RNAErnie.md) | 12-layer Transformer (motif-aware MLM) | **768-d** | Mean (excl CLS+SEP) | 23M ncRNAs (RNAcentral) | 2046 nt | ~4 GB | ~1.5 GB |
| [PlantRNA-FM](models/PlantRNAFM.md) | 12-layer ESM Transformer (35M params) | **480-d** | Mean (excl CLS+EOS) | ~25M plant RNAs (1124 species, 54.2B bases) | 1024 nt | ~3 GB | ~1.2 GB |
| [CaLM](models/CaLM.md) | 12-layer Transformer (~86M params) | **768-d** | Mean (excl CLS+EOS) | ~9M CDSs (cross-organism ENA codingseqs) | 1024 codons (~3 kb) | ~3 GB | ~1.2 GB |
| [mRNABERT](models/mRNABERT.md) | 12-layer MosaicBERT + ALiBi (~86M params) | **768-d** | Mean (excl CLS+SEP) | ~18M full-length mRNAs | 1024 tokens (hybrid 1-nt UTR + 3-nt CDS codons) | ~3 GB | ~1.2 GB |
| [HydraRNA](models/HydraRNA.md) | 12-layer hybrid Hydra-SSM + 2 attention layers (~84M params) | **1024-d** | Mean (excl BOS+EOS) | ~73M ncRNAs + ~22M mRNAs | 10K nt (auto-chunked beyond) | ~7 GB | — (GPU only) |

**Pooling note:** values reflect the as-implemented behavior of the wrapper scripts in `bin/`. ERNIE-RNA is the only foundation model using the `[CLS]` token as the per-sequence representation; the other four mean-pool over actual sequence positions (excluding special tokens). This matters when comparing embeddings across models — `[CLS]` from an MLM-only model is qualitatively different from a position-mean.

### Specialized models

The remaining 12 models are task-specific predictors across translation, structure, modification, and mRNA design. Each uses its native input/output format — see the linked model card for details.

| Model | Track | Training set | Input | Output | GPU image | CPU image |
|-------|-------|--------------|-------|--------|-----------|-----------|
| [RiboNN](models/RiboNN.md) | Translation | 78 human cell-type TE | TSV (`tx_id`, UTR5, CDS, UTR3) | per-cell-type TE TSV | 2.8 GB | 1.2 GB |
| [Riboformer](models/Riboformer.md) | Translation | ribo-seq, 5 species | Dir (WIG + GFF + FASTA) | `model_prediction.txt` | 4.0 GB | 2.3 GB |
| [RiboTIE](models/RiboTIE.md) | Translation | human ribo-seq (8 SRRs) | Dir (FASTA + GTF + BAMs + YAML) | per-sample GTF / CSV / NPY | 3.9 GB | 1.3 GB |
| [seq2ribo](models/seq2ribo.md) | Translation | 4 human cell-line ribo-seq + sTASEP sim | FASTA mRNA | `seq2ribo_output.json` | 10.3 GB | — (GPU only) |
| [TranslationAI](models/TranslationAI.md) | Translation | 47K human RefSeq mRNAs | FASTA mRNA | `*_predTIS` / `*_predTTS` / `*_predORFs.txt` | 1.9 GB | 0.6 GB |
| [Saluki](models/Saluki.md) | Translation | 66 mRNA-decay datasets (human + mouse) | FASTA (UTR lowercase, CDS UPPERCASE) | `preds.npy` | 4.2 GB | 1.4 GB |
| [CodonTransformer](models/CodonTransformer.md) | Translation | 1M genes across 164 organisms | FASTA protein | optimized DNA FASTA | 3.7 GB | 1.2 GB |
| [RNAformer](models/RNAformer.md) | Structure | bpRNA + PDB (LoRA-finetuned) | FASTA RNA | `structures.txt` (dot-bracket) | 3.8 GB | — (single image) |
| [RhoFold](models/RhoFold.md) | Structure | PDB + bpRNA self-distillation | FASTA RNA | PDB + `ss.ct` + `results.npz` | 4.2 GB | 1.7 GB |
| [SPOT-RNA](models/SPOTRNA.md) | Structure | bpRNA + PDB + Rfam | FASTA RNA | `structures.txt` + per-seq `bpseq` / `ct` / `prob` | 2.7 GB | 0.6 GB |
| [DRfold2](models/DRfold2.md) | Structure (Tier 2) | bpRNA + PDB single-seq | FASTA RNA | per-seq PDB | ~5 GB | — (GPU only) |
| [MultiRM](models/MultiRM.md) | Modification | ~300K human modification sites | FASTA RNA | `modification_scores.tsv` + `predicted_sites.tsv` | 3.5 GB | 1.0 GB |
| [Pangolin](models/Pangolin.md) | Splicing | 4-tissue (heart/liver/brain/testis) human + 3 species | VCF/CSV + ref FASTA + gffutils DB | annotated VCF/CSV | ~3 GB | ~3 GB |
| [SpliceAI](models/SpliceAI.md) | Splicing | 1k human variants per gene (Cell 2019) | VCF + ref FASTA + annotation | annotated VCF (4-class delta) | ~2.3 GB | ~2.3 GB |
| [SpliceBERT](models/SpliceBERT.md) | Splicing | 2M+ vertebrate primary RNAs (72 species) | FASTA RNA | NumPy (N x 512) | ~3 GB | ~1.2 GB |
| [UTR-LM](models/UTRLM.md) | mRNA Design | 5'UTRs, 5 species + MPRA (MRL) | FASTA 5'UTR | `predictions.tsv` | 4.9 GB | 2.4 GB |

**Totals:** CPU set is **~39 GB** across 21 images; GPU set is **~103 GB** across 25 images. See the [installation page](getting-started/installation.md) for the matching pre-pull commands.

## Quick start

### With Nextflow (recommended for pipelines)

```bash
# Run the test suite (13 models on CPU, ~5 min)
nextflow run . -profile test,docker,cpu

# Run a single model — only models you provide input for will run
nextflow run . -profile docker,cpu --rnafm_input my_sequences.fa

# Run multiple models in parallel
nextflow run . -profile docker,cpu \
  --rnafm_input seqs.fa \
  --rnaformer_input seqs.fa \
  --multirm_input seqs.fa

# Use a YAML params file for complex runs
nextflow run . -profile docker,cpu -params-file my_params.yml
```

### With plain Docker (no Nextflow required)

```bash
# Run one model against a FASTA (CPU)
docker run --rm \
    -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
    -v $PWD/seqs.fa:/data/input.fa -v $PWD/out:/out \
    ghcr.io/ericmalekos/rnazoo-rnafm-cpu:latest \
    rnafm_predict.py -i /data/input.fa -o /out
```

See the [Direct Docker guide](direct-docker.md) for invocations of every model.

## Design principles

- **One Docker image per model** — weights baked in at build time, no runtime downloads
- **GPU by default** — the test suite and per-model docs assume `--profile gpu`; foundation and structure models are 30–60× faster on GPU than CPU
- **CPU supported for small runs** — most models also ship a `-cpu` image; pick `--profile cpu` for laptop / no-GPU use, with the caveat that GPU-only models (seq2ribo, Orthrus) auto-skip with a warning
- **Portable** — runs anywhere with Docker or Singularity + Nextflow

## License

RNAZoo pipeline code is open source. Individual models carry their own licenses — see each model's page for details. Most are MIT/Apache-2.0; some have non-commercial restrictions noted on their pages.
