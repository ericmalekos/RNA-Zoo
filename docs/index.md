# RNAZoo

**A Nextflow pipeline model zoo for RNA deep learning.**

RNAZoo packages 15 state-of-the-art RNA ML models into a single, portable Nextflow pipeline with Docker/Singularity containers. Each model has baked-in weights — no runtime downloads, no dependency conflicts.

## What's included

15 models across 5 tracks. Every container has its model weights baked in at build time — no runtime downloads. Image sizes below are the **compressed download size** from GHCR; on disk they roughly double after extraction.

| Model | Track | Input | Output | GPU image | CPU image |
|-------|-------|-------|--------|-----------|-----------|
| [RiboNN](models/RiboNN.md) | Translation | TSV (`tx_id`, UTR5, CDS, UTR3) | per-cell-type TE TSV | 2.8 GB | 1.2 GB |
| [Riboformer](models/Riboformer.md) | Translation | Dir (WIG + GFF + FASTA) | `model_prediction.txt` | 4.0 GB | 2.3 GB |
| [RiboTIE](models/RiboTIE.md) | Translation | Dir (FASTA + GTF + BAMs + YAML) | per-sample GTF / CSV / NPY | 3.9 GB | 1.3 GB |
| [seq2ribo](models/seq2ribo.md) | Translation | FASTA mRNA | `seq2ribo_output.json` | 10.3 GB | — (GPU only) |
| [TranslationAI](models/TranslationAI.md) | Translation | FASTA mRNA | `*_predTIS` / `*_predTTS` / `*_predORFs.txt` | 1.9 GB | 0.6 GB |
| [Saluki](models/Saluki.md) | Translation | FASTA (UTR lowercase, CDS UPPERCASE) | `preds.npy` | 4.2 GB | 1.4 GB |
| [CodonTransformer](models/CodonTransformer.md) | Translation | FASTA protein | optimized DNA FASTA | 3.7 GB | 1.2 GB |
| [RNA-FM](models/RNAFM.md) | Foundation | FASTA RNA | `sequence_embeddings.npy` + `labels.txt` | 4.2 GB | 1.7 GB |
| [RiNALMo](models/RiNALMo.md) | Foundation | FASTA RNA | `sequence_embeddings.npy` + `labels.txt` | 5.6 GB | 3.1 GB |
| [ERNIE-RNA](models/ERNIERNA.md) | Foundation | FASTA RNA | `sequence_embeddings.npy` + `labels.txt` | 5.7 GB | — (single image) |
| [RNAformer](models/RNAformer.md) | Structure | FASTA RNA | `structures.txt` (dot-bracket) | 3.8 GB | — (single image) |
| [RhoFold](models/RhoFold.md) | Structure | FASTA RNA | PDB + `ss.ct` + `results.npz` | 4.2 GB | 1.7 GB |
| [SPOT-RNA](models/SPOTRNA.md) | Structure | FASTA RNA | `structures.txt` + per-seq `bpseq` / `ct` / `prob` | 2.7 GB | 0.6 GB |
| [MultiRM](models/MultiRM.md) | Modification | FASTA RNA | `modification_scores.tsv` + `predicted_sites.tsv` | 3.5 GB | 1.0 GB |
| [UTR-LM](models/UTRLM.md) | mRNA Design | FASTA 5'UTR | `predictions.tsv` | 4.9 GB | 2.4 GB |

**Totals:** CPU set is **~28 GB** across 14 images; GPU set is **~65 GB** across 15 images. See the [installation page](getting-started/installation.md) for the matching pre-pull commands.

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
- **CPU by default** — GPU-only models auto-skip under `--profile cpu`
- **Per-model input/output** — each model uses its native format, no forced preprocessing
- **Portable** — runs anywhere with Docker or Singularity + Nextflow

## License

RNAZoo pipeline code is open source. Individual models carry their own licenses — see each model's page for details. Most are MIT/Apache-2.0; some have non-commercial restrictions noted on their pages.
