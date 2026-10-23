# RNAZoo

A Nextflow pipeline that runs 23 RNA deep learning models, each from its own container image.

## What's included

The 23 models fall into six tracks: 13 task programs and 10 embedding models (the nine
foundation models and SpliceBERT). The [model overview](models/overview.md) lists each model's
task, input, output, GPU needs and license.

| Track | Models |
|-------|--------|
| Translation | [RiboNN](models/RiboNN.md), [Riboformer](models/Riboformer.md), [RiboTIE](models/RiboTIE.md), [TranslationAI](models/TranslationAI.md), [Saluki](models/Saluki.md), [CodonTransformer](models/CodonTransformer.md) |
| RNA foundation models | [RNA-FM](models/RNAFM.md), [RiNALMo](models/RiNALMo.md), [ERNIE-RNA](models/ERNIERNA.md), [Orthrus](models/Orthrus.md), [HydraRNA](models/HydraRNA.md), [RNAErnie](models/RNAErnie.md), [PlantRNA-FM](models/PlantRNAFM.md), [CaLM](models/CaLM.md), [mRNABERT](models/mRNABERT.md) |
| RNA structure | [RhoFold](models/RhoFold.md), [SPOT-RNA](models/SPOTRNA.md), [DRfold2](models/DRfold2.md) |
| RNA modification | [MultiRM](models/MultiRM.md) |
| Splicing | [Pangolin](models/Pangolin.md), [SpliceAI](models/SpliceAI.md), [SpliceBERT](models/SpliceBERT.md) |
| mRNA design | [UTR-LM](models/UTRLM.md) |

Each embedding model writes one vector per sequence (`sequence_embeddings.npy`, with the
sequence names in `labels.txt`) and, with `--<model>_per_token`, one per token. All but
SpliceBERT can train a prediction head on your labels ([Fine Tuning](finetuning.md)).

## How it runs

- Each model has its own image, `ghcr.io/ericmalekos/rnazoo-<name>`, with the weights inside, so
  nothing is downloaded at run time. Most models have a GPU image and a smaller CPU image.
- A model runs only when its input parameter is set, so one command can run one model or
  several in parallel.
- Docker or Singularity runs the images. Add `gpu` or `cpu` to the profile. Orthrus, HydraRNA
  and DRfold2 need a GPU and are skipped under `cpu`.

## Quick start

From the cloned repository, with Nextflow and Docker installed
([Installation](getting-started/installation.md)):

```bash
# Test run: 19 models on the test inputs in tests/data/
nextflow run main.nf -profile test,docker,cpu

# One model on your own FASTA
nextflow run main.nf -profile docker,cpu --rnafm_input my_sequences.fa
```

On a machine with an NVIDIA GPU, write `gpu` instead of `cpu`. The
[Quick Start](getting-started/quickstart.md) shows more options, and
[Direct Docker usage](direct-docker.md) runs the images without Nextflow.

## License

The RNA-Zoo pipeline code is released under the MIT License. Each model keeps its own terms for
its code, weights and container image, listed in the [model overview](models/overview.md#licenses)
and on its page: some forbid commercial use, and for some the weights carry no license
statement, which leaves their use unclear. Please cite RNA-Zoo
([CITATION.cff](https://github.com/ericmalekos/RNA-Zoo/blob/main/CITATION.cff)) and the paper of
every model you run.
