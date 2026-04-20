# RNAZoo

**A Nextflow pipeline model zoo for RNA deep learning.**

RNAZoo packages 15 state-of-the-art RNA ML models into a single, portable Nextflow pipeline with Docker/Singularity containers. Each model has baked-in weights — no runtime downloads, no dependency conflicts.

## What's included

| Track | Models | What they predict |
|-------|--------|-------------------|
| **Translation** | RiboNN, Riboformer, RiboTIE, seq2ribo, TranslationAI, Saluki, CodonTransformer | Translation efficiency, ribosome profiling, ORF detection, mRNA half-life, codon optimization |
| **RNA Foundation** | RNA-FM, RiNALMo, ERNIE-RNA | General-purpose RNA embeddings (640-d, 1280-d, 768-d) |
| **RNA Structure** | RNAformer, RhoFold, SPOT-RNA | 2D base-pair prediction, 3D structure prediction (PDB), pseudoknot detection |
| **RNA Modification** | MultiRM | 12 RNA modification types (m6A, m5C, pseudouridine, etc.) |
| **mRNA Design** | UTR-LM | 5'UTR mean ribosome loading, translation efficiency, expression level |

## Quick start

```bash
# Run the test suite (12 models on CPU, ~3 min)
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

## Design principles

- **One Docker image per model** — weights baked in at build time, no runtime downloads
- **CPU by default** — GPU-only models auto-skip under `--profile cpu`
- **Per-model input/output** — each model uses its native format, no forced preprocessing
- **Portable** — runs anywhere with Docker or Singularity + Nextflow

## License

RNAZoo pipeline code is open source. Individual models carry their own licenses — see each model's page for details. Most are MIT/Apache-2.0; some have non-commercial restrictions noted on their pages.
