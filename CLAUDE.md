Goals:
- Create a broad RNA ML toolkit "model zoo" where AI/ML RNA models can easily be run.
- Scope includes multiple tracks:
  - **translation**: TE prediction, ribosome profiling, ORF detection, codon optimization
  - **ribo-seq refinement**: models that refine/denoise experimental ribo-seq data
  - **RNA structure**: secondary and 3D structure prediction from sequence
  - **splicing**: splice site and alternative splicing prediction from sequence
  - **RNA modification**: m6A and other modification site prediction from sequence
  - **mRNA design**: UTR optimization, poly(A) prediction, stability design
  - **RNA foundation models**: general-purpose RNA language models / embeddings
- Package in a portable nextflow pipeline, modeled on the nf-core repo structure with a "workflow" folder and a "modules" folder for individual models
- The pipeline should be able to run in Docker or Singularity compatible environments.
- Code should be uniform and "linted" and badges for linting and CI/CD test passing should be included for Github repo.

Plan:
- Create Docker images for each model.
- Create both a CPU and GPU variant so that it can be run in CPU only environments whenever possible.
- When possible preprocess the input so that a minimal input can be broadly processed for various models.
- Add tests for CI/CD style development.
- Default pipeline should run all models, with --ignore_<modelname> set as a flag to ignore running any models the user does not want.

================================================================================
TRANSLATION TRACK (integrated)
================================================================================

- RiboNN          https://github.com/Sanofi-Public/RiboNN   https://www.nature.com/articles/s41587-025-02712-x
- Riboformer      https://github.com/lingxusb/Riboformer    https://www.nature.com/articles/s41467-024-46241-8
- RiboTIE         https://github.com/TRISTAN-ORF/TRISTAN    https://www.nature.com/articles/s41467-025-56543-0    (upstream "RiboTIE" repo archived; wrapping maintained successor TRISTAN / transcript_transformer v1.1.1)
- seq2ribo        https://github.com/Kingsford-Group/seq2ribo   https://www.biorxiv.org/content/10.64898/2026.02.08.700508v1    (GPU-only; CMU Academic/Non-Commercial license — publish with notice)
- TranslationAI   https://github.com/rnasys/TranslationAI    https://academic.oup.com/nar/article/53/7/gkaf277/8112693    (AGPL-3.0 source + CC BY-NC 4.0 weights)
- Saluki          https://github.com/calico/basenji    https://genomebiology.biomedcentral.com/articles/10.1186/s13059-022-02811-x    (Apache 2.0; weights from Zenodo 18.8 GB archive)
- CodonTransformer https://github.com/Adibvafa/CodonTransformer    https://www.nature.com/articles/s41467-025-58588-7    (Apache 2.0; pip + HuggingFace weights)

================================================================================
RNA FOUNDATION MODELS (integrated)
================================================================================

- RNA-FM          https://github.com/ml4bio/RNA-FM    Nat. Mach. Intell. 2024    (general RNA embeddings; MIT; PyTorch; pip-installable)
- RiNALMo         https://github.com/lbcb-sci/RiNALMo    NeurIPS 2024    (650M-param RNA LM; Apache-2.0; PyTorch; non_flash branch for CPU compat)
- ERNIE-RNA       https://github.com/Bruce-ywj/ERNIE-RNA    Nat. Commun. 2025    (structure-aware RNA LM; embeddings + SS + 3D closeness + MRL; MIT; PyTorch+fairseq) — integrated
- BiRNA-BERT      https://github.com/buetnlpbio/BiRNA-BERT    Briefings Funct. Genomics 2025    (RNA LM with adaptive dual tokenization; ~480M params; HuggingFace-native) — deferred: NO LICENSE on repo or HuggingFace, cannot redistribute without author permission

================================================================================
RNA STRUCTURE (Tier 1 integrated, Tier 2 to add)
================================================================================

- RNAformer       https://github.com/automl/RNAformer    ICLR 2024    (2D structure / base-pair matrix; Apache-2.0; PyTorch) — integrated
- RhoFold         https://github.com/ml4bio/RhoFold    Nat. Methods 2024    (3D structure from sequence; Apache-2.0; PyTorch; single-sequence mode) — integrated
- SPOT-RNA        https://github.com/jaswindersingh2/SPOT-RNA    Nat. Commun. 2019    (2D structure incl. pseudoknots; MPL-2.0; TensorFlow) — integrated

================================================================================
SPLICING (to add — Tier 1 + Tier 2)
================================================================================

- SpliceAI        https://github.com/Illumina/SpliceAI    Cell 2019    (splice site prediction; PolyForm Strict 1.0.0 source + CC BY-NC 4.0 weights — non-commercial only; TF/Keras; pip-installable; 2500+ citations) — deferred
- Pangolin        https://github.com/tkzeng/Pangolin    Genome Biol. 2022    (tissue-specific splice usage; MIT; PyTorch) — deferred
- SpliceBERT      https://github.com/biomed-AI/SpliceBERT    Nat. Commun. 2024    (splice pretrained model; BSD-3; PyTorch) — deferred

================================================================================
RNA MODIFICATION (to add — Tier 1)
================================================================================

- MultiRM         https://github.com/Tsedao/MultiRM    NAR 2021    (12 RNA modification types from sequence; MIT; PyTorch) — integrated

================================================================================
mRNA DESIGN / UTR (to add — Tier 1 + Tier 2)
================================================================================

- UTR-LM          https://github.com/a96123155/UTR-LM    Nat. Mach. Intell. 2024    (5'UTR language model for expression/stability; GPL-3.0; PyTorch) — integrated
- APARENT          https://github.com/johli/aparent    Cell Systems 2019    (poly(A) signal strength; MIT; Keras) — deferred

================================================================================
DEFERRED
================================================================================

- Enigma          https://github.com/deepgenomics/enigma — fine-tuned TE weights NOT released, Deep Genomics Non-Commercial license, FlashAttention GPU required, wandb-gated, no CLI
- Optimus 5-Prime https://github.com/pjsample/human_5utr_modeling — Python 2.7, notebook-only, no CLI, no saved StandardScaler, needs wrapper + scaler reconstruction
- RNA-MSM         https://github.com/yikunpku/RNA-MSM — requires MSA input (not pure single-sequence)
- 3UTRBERT        https://github.com/yangyn533/3UTRBERT    Adv. Sci. 2024 — MIT; Python 3.6 requirement, no CLI, overlaps MultiRM + UTR-LM; HuggingFace port (multimolecule/utrbert-6mer) could reduce friction later
- LAMAR           https://github.com/zhw-e8/LAMAR    bioRxiv 2024 — MIT; preprint only, 15 stars, notebook-only, heavily overlaps RNA-FM/RiNALMo/UTR-LM/SpliceAI; revisit if published

================================================================================
DROPPED
================================================================================

- RiboMIMO        https://github.com/tiantz17/RiboMIMO — no LICENSE, no weights, no CLI, stale, yeast/E. coli only
- RiboDecode      https://github.com/wangfanfff/RiboDecode — no LICENSE, no source code, binary-only .whl via Google Drive
- RNA-ERNIE       https://github.com/CatIIIIIIII/RNAErnie — PaddlePaddle framework (not PyTorch/TF), packaging friction
- LinearDesign    https://github.com/LinearDesignSoftware/LinearDesign — C++ (not Python ML model), academic license
- DeepRiPe        https://github.com/ohlerlab/DeepRiPe — unclear license
- G4mer           https://bitbucket.org/biociphers/g4mer — UPenn Academic/Non-Commercial license, gated HuggingFace weights, cannot bake into public Docker images

================================================================================
FUTURE (code unavailable)
================================================================================

- Translatomer    https://www.biorxiv.org/content/10.1101/2024.02.26.582217v1

================================================================================
INSTRUCTIONS
================================================================================

- Add each model in the order listed above (translation track first, then foundation models, structure, splicing, modification, design).
- For each model, complete ALL of the following before moving to the next:
  1. **Build** Docker image (CPU + GPU variants where applicable).
  2. **Test standalone**: run the Docker image directly with test data, verify output.
  3. **Test in Nextflow**: run through the pipeline with `-profile docker,cpu` (and `-profile docker,gpu` if applicable), verify outputs land in `results/`.
  4. **Test data**: commit a minimal test input file to `tests/data/` if one does not already exist.
  5. **Document**: write a README in `docs/models/<ModelName>.md` covering: what the model does, input/output formats with examples, Docker run command, Nextflow run command, parameter table, and example output.
  6. **Tests pass**: all existing tests and linter checks still pass (`ruff check .`, `nf-core lint`).
  7. **Flag issues**: if the model has known bugs or limitations, document them in the model README and in a separate `docs/<issue_dir>/` with a minimal reproduction if upstream.

================================================================================
FINE-TUNING / RETRAINING SUPPORT
================================================================================

Goal: where upstream models support fine-tuning on user data, expose that
capability through the pipeline alongside the existing inference mode.

Status key: DONE = exposed in pipeline, TODO = upstream supports it but not yet
wired, N/A = inference-only (frozen weights).

| Model         | Status | Upstream capability |
|---------------|--------|---------------------|
| RiboTIE       | DONE   | Fine-tunes pretrained transformer on user's ribo-seq BAMs before ORF prediction. Controlled via ribotie_max_epochs / ribotie_patience. |
| RiboNN        | DONE   | Transfer learning via RIBONN_FINETUNE process. Freezes pretrained conv layers, trains head on user TE data with 2-phase training + early stopping. |
| UTR-LM        | DONE   | Fine-tuning via UTRLM_FINETUNE process. Trains ESM2 backbone + FC head on user MRL/TE/EL data with train/val split + early stopping. |
| ERNIE-RNA     | TODO   | Upstream has fine-tuning scripts for SS prediction, 3D closeness, and MRL. Currently only embedding extraction is exposed. |
| Riboformer    | TODO   | transfer.py applies pretrained model to new data; upstream also has train code for new organisms/conditions. |
| RNAformer     | PARTIAL| Ships LoRA-finetuned checkpoints; users can swap via --config/--state-dict. No training loop exposed yet. |
| RNA-FM        | N/A    | Foundation model, inference-only. |
| RiNALMo       | N/A    | Foundation model, inference-only. |
| SPOT-RNA      | N/A    | 5-model frozen ensemble. |
| RhoFold       | N/A    | Frozen pretrained model. |
| CodonTransformer | N/A | Frozen pretrained model. |
| MultiRM       | N/A    | Frozen 12-task LSTM. |
| seq2ribo      | N/A    | Frozen Mamba SSM. |
| Saluki        | N/A    | Frozen 50-member CNN ensemble. |
| TranslationAI | N/A    | Frozen TIS/TTS predictor. |

Priority order for adding fine-tuning:
1. RiboNN (transfer learning — straightforward, upstream Makefile has targets)
2. UTR-LM (MRL/TE/EL fine-tuning — training scripts exist, need wrapping)
3. ERNIE-RNA (SS/MRL fine-tuning — scripts exist, need device patches like inference)
4. Riboformer (train on new organism — needs data prep pipeline)
5. RNAformer (expose LoRA training — more complex, needs training data pipeline)

================================================================================
DECISIONS
================================================================================

- **Input:** per-model, as the upstream authors intended. Revisit after surveying all models to see if a generic preprocessing step is worth adding.
- **Output:** per-model output directories.
- **Preprocessing:** none for now — each module passes through the author's native input format.
- **Container registry:** ghcr.io/ericmalekos (public, unlimited, co-located with code).
- **Model weights:** baked into Docker images at build time. No runtime downloads.
- **GPU/CPU:** default to model's native (typically GPU); user passes `--profile cpu` to force CPU. GPU-only models auto-skip with a warning under `--profile cpu`.
- **Linting:** python = ruff, nextflow = `nf-core lint`.
- **CI:** GitHub Actions on GitHub-hosted runners, CPU-only. GPU verified manually before releases.
- **Testing:** per-model unit tests + pipeline end-to-end test with a minimal transcript set.
- **Repo structure:** public repo excludes model clones (gitignored or moved elsewhere); Dockerfiles clone from upstream at build time.
