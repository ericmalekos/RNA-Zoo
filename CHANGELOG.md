# Changelog

## 1.0.0 (unreleased)

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
