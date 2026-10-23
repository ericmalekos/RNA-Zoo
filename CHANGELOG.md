# Changelog

## 1.0.1 (2026-10-23)

### Fixed
- The Saluki images failed to build for 1.0.0: basenji's `requirements.txt` pins nothing, and
  pybedtools 0.12.1 (released 2026-08-26) does not build on the images' Python 3.8. The Saluki
  Dockerfiles now check out basenji at a fixed commit (`06ce5d3`) and install its requirements
  under `Dockerfiles/constraints/saluki.txt`, the package versions of the previously published
  Saluki image. The model code is unchanged.
- The 1.0.0 rebuild of every image pulled the newest versions of unpinned dependencies. RiboTIE
  broke (polars 2.0 removed an API that transcript_transformer uses), and CaLM's CPU image
  replaced its CPU torch 2.2 with a CUDA build of torch 2.14. Both now install under
  constraints holding every package at the version of the previously published image
  (`Dockerfiles/constraints/{tristan,calm}.txt`), with torch pinned (RiboTIE 2.5.1, CaLM 2.2)
  and CaLM's repository at a fixed commit. A test of the other rebuilt CPU images on the
  pipeline's test data found no failure.
- `bin/saluki_predict.py` was not executable, so the pipeline could not run the new Saluki
  wrapper (the 1.0.0 pipeline test failed on this); `scripts/check_model_count.py` and
  `scripts/pin_container_digests.py` are executable too.

### Documentation
- The license statements in the README, the model overview and the model pages now separate
  code from weights wherever their terms differ, as the overview's license table already did:
  CaLM, ERNIE-RNA and SPOT-RNA state no license for their weights (CaLM's page had applied
  BSD-3-Clause to them); RNA-FM's weights are Apache-2.0, RiNALMo's and SpliceBERT's CC BY 4.0;
  Riboformer and RiboTIE are MIT for code and weights. The same corrections reach the module
  and wrapper comments (CaLM, DRfold2, SpliceAI) and the images' `licenses` labels: images
  whose weights state no terms (CaLM, DRfold2, SpliceAI) are labeled `NOASSERTION` with the
  details in their description, SpliceBERT `BSD-3-Clause AND CC-BY-4.0`.

## 1.0.0 (2026-10-23)

### Changed
- Orthrus loads the large 4-track checkpoint (`quietflamingo/orthrus-large-4-track`) by
  default; the earlier default (`antichronology/orthrus-4-track`, `--orthrus_variant 4track`)
  fails at ortholog retrieval and at coding versus noncoding classification.
- Saluki runs through a new wrapper (`bin/saluki_predict.py`) that sets the splice-junction
  input channel from exon lengths (`--saluki_exons`), as the model was trained, writes
  `predictions.tsv` beside `preds.npy`, and documents the output as Saluki's unitless
  consensus half-life score, not log2 half-life. Outputs move to `saluki/saluki_out/`.
- TranslationAI uses its CPU image under both profiles: its command-line entry point sets
  `CUDA_VISIBLE_DEVICES=-1`, so the GPU image never used a GPU.
- Every process requests `--task_cpus` CPUs (default 4), and the thread limits of OpenMP, MKL,
  OpenBLAS, NumExpr, TensorFlow, Rayon and Numba inside each container follow it.
  `TF_FORCE_GPU_ALLOW_GROWTH`, `TMPDIR=/tmp` and `TRITON_CACHE_DIR` are set in every
  container.
- SpliceAI and Pangolin stage the reference FASTA's `.fai` when one exists beside the FASTA,
  instead of re-indexing the genome in every run.
- The fine-tuning head trainer accepts `--split-file` (one `train` or `test` per row) and
  reports held-out test metrics.

### Fixed
- MultiRM scored only the first trinucleotide of each 51-nt window: the prediction script,
  like upstream's `Scripts/main.py`, transposed the k-mer tensor so the model saw 49 inputs of
  length one. Scores now respond to the center base.
- SPOT-RNA always ran on 4 CPU threads and never on the GPU; it now uses the GPU under the
  GPU profile and the task's CPUs, and fails when a sequence produces no structure instead of
  writing a structures file that silently lacks it.
- RiboNN's GPU image held a CPU-only PyTorch build; the CUDA build is now selected at image
  build time and checked.
- CodonTransformer's baked weights were unreadable to non-root Singularity users, so every
  run downloaded them; they now live in `/opt/codontransformer_model`.
- `--spotrna_plot false` and `--multirm_plot false` on the command line no longer turn
  plotting on.
- SpliceAI images include `ps`, which Nextflow's trace needs.
- Riboformer reports a clear error when too few genes pass its normalization, instead of a
  bare numpy IndexError.

### Documentation
- RNA-Zoo's own code is released under the MIT License (`LICENSE`); each model keeps its
  own terms.
- Licenses are stated as published for every model, including those whose weights carry no
  license statement; RiboNN, SpliceAI and DRfold2 images are redistributed with their
  authors' permission.
- RiboNN predicts 78 human cell types (not 82); model counts read 23 (13 task programs and
  10 embedding models) everywhere, checked in CI against the modules.
