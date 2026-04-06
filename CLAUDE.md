Goals:
- Create a broad riboseq ML toolkit "model zoo" where AI/ML riboseq models can easily be run.
- Scope includes two tracks:
  - **sequence→prediction**: models that take mRNA sequences and predict TE, ribosome density, etc. (e.g. RiboNN)
  - **ribo-seq refinement/correction**: models that take experimental ribo-seq data (WIG/BAM/coverage) and refine/denoise/correct it (e.g. Riboformer)
- Package in a portable nextflow pipeline, modeled on the nf-core repo structure with a "workflow" folder and a "modules" folder for individual models
- The pipeline should be able to run in Docker or Singularity compatible environments.
- code should be uniform and "linted" and a badges for linting and CI/CD test passing should be included for Github repo.

Plan:
- Create Docker images for each model.
- create both a CPU and GPU so that it can be run in CPU only environment whenever possible.
- When possible preprocess the input so that a minimal input can be broadly processed for various models.
- add tests for CI/CD style development
- Default pipeline should run all model, with --ignore_<modelname> set as a flag to ignore running any models the user does not want

Models included (integrated):
- RiboNN          https://github.com/Sanofi-Public/RiboNN   https://www.nature.com/articles/s41587-025-02712-x
- Riboformer      https://github.com/lingxusb/Riboformer    https://www.nature.com/articles/s41467-024-46241-8
- RiboTIE         https://github.com/TRISTAN-ORF/TRISTAN    https://www.nature.com/articles/s41467-025-56543-0    (upstream "RiboTIE" repo is archived; wrapping the maintained successor TRISTAN / transcript_transformer v1.1.1)
- seq2ribo        https://github.com/Kingsford-Group/seq2ribo   https://www.biorxiv.org/content/10.64898/2026.02.08.700508v1    (GPU-only; CMU Academic/Non-Commercial license — publish with notice)
- TranslationAI   https://github.com/rnasys/TranslationAI    https://academic.oup.com/nar/article/53/7/gkaf277/8112693    (TIS/TTS/ORF detection from mRNA sequence; AGPL-3.0 source + CC BY-NC 4.0 weights)
- CodonTransformer https://github.com/Adibvafa/CodonTransformer    https://www.nature.com/articles/s41467-025-58588-7    (codon optimization; Apache 2.0; protein seq → optimized DNA; 164 organisms; HuggingFace weights)

- Saluki          https://github.com/calico/basenji    https://genomebiology.biomedcentral.com/articles/10.1186/s13059-022-02811-x    (mRNA half-life from sequence; Apache 2.0; weights from Zenodo 18.8 GB archive; human + mouse)
- Optimus 5-Prime https://github.com/pjsample/human_5utr_modeling    https://www.nature.com/articles/s41587-019-0164-5    (5'UTR → MRL; GPL-3.0; deferred: Python 2.7 notebook-only repo, no CLI, no saved StandardScaler, needs wrapper script written from scratch + scaler reconstruction from GEO training data)
- CodonTransformer https://github.com/Adibvafa/CodonTransformer    https://www.nature.com/articles/s41467-025-58588-7    (codon optimization / generative; Apache 2.0; pip-installable + HuggingFace weights; 164 organisms; needs CLI wrapper script)

Deferred:
- Enigma          https://github.com/deepgenomics/enigma — in scope for TE prediction (paper demonstrates it) but: fine-tuned TE weights NOT released (only base model available), Deep Genomics custom Non-Commercial license, mandatory FlashAttention GPU (Ampere+), weights gated behind wandb login, no CLI, 2 commits. Defer until fine-tuned weights are released.

Dropped:
- RiboMIMO        https://github.com/tiantz17/RiboMIMO — no LICENSE file (blocks redistribution), no pretrained weights, no inference-only CLI, training-focused repo, stale (2020, PyTorch 1.5/CUDA 10.2), yeast/E. coli only, non-standard input format (pre-processed ribo-seq codon+count 3-line format), GPU required. Task also differs fundamentally (per-codon density from observed ribo-seq, not TE from sequence).
- RiboDecode      https://github.com/wangfanfff/RiboDecode — no LICENSE file, no source code in repo (binary-only .whl files distributed via Google Drive), opaque/unauditable, CUDA 12.1 required.

Future models (code unavailable)
- Translatomer    https://www.biorxiv.org/content/10.1101/2024.02.26.582217v1


Instructions:
- Add each model in the order listed above.
- Before moving on to the next model test the Docker image in an out of Nextflow pipeline and with GPU and CPU flagging any issues.
- Before moving on make sure the model run passes tests and all previous tests are passed.
- Before moving on make sure linter passes checks.

Decisions:
- **Input:** per-model, as the upstream authors intended. Revisit after surveying all models to see if a generic preprocessing step (genome FASTA + GTF + tx IDs) is worth adding.
- **Output:** per-model output directories.
- **Preprocessing:** none for now — each module passes through the author's native input format.
- **Container registry:** ghcr.io (public, unlimited, co-located with code).
- **Model weights:** baked into Docker images at build time (downloaded during `docker build`, then embedded as image layers). No runtime downloads.
- **GPU/CPU:** default to model's native (typically GPU); user passes `--profile cpu` to force CPU. GPU-only models auto-skip with a warning under `--profile cpu`.
- **Linting:** python = ruff, nextflow = `nf-core lint`.
- **CI:** GitHub Actions on GitHub-hosted runners, CPU-only. GPU verified manually before releases.
- **Testing:** per-model unit tests + pipeline end-to-end test with a minimal transcript set.
- **Repo structure:** public repo excludes model clones (gitignored or moved elsewhere); Dockerfiles clone from upstream at build time.