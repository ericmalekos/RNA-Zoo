# Changelog

## 1.0.4 (2026-11-02)

### Fixed
- Orthrus `--per-token` (`--orthrus_per_token true`) stopped with an AttributeError for the default
  `large-4track` and for `base-4track` and `large-6track`, whose model code has no
  `representation_unpooled`. The wrapper now takes the model's forward output, which is what that
  method returns for the other checkpoints.
- DRfold2 `--cluster` could run without end: upstream's clustering step moves its RMSD cutoff in
  0.2 Å steps and on some inputs, the test hairpin among them, alternates between two cutoffs. The
  wrapper now stops it once the top model has been written for `--drfold2_cluster_timeout` seconds
  (default 600) without a cluster list, keeps the top model and warns.
- HydraRNA run directly with `singularity exec --no-home` stopped when Triton wrote its kernel cache
  to the read-only home folder; the image now sets `TRITON_CACHE_DIR=/tmp/triton`, as the pipeline does.

## 1.0.3 (2026-11-02)

### Added
- `conf/containers_v1.0.2.config` pins every image to its v1.0.2 registry digest; pass it with
  `nextflow -c` and run the v1.0.2 code (`-r v1.0.2`) to run exactly the release images.

### Fixed
- A command-line `false` turned on flags it should leave off: every `--<model>_per_token`, DRfold2's
  `--drfold2_cluster` and `--drfold2_keep_intermediate`, and `--codontransformer_deterministic false`
  kept CodonTransformer deterministic. Nextflow passes command-line values as strings, and the
  string "false" counts as true; the modules now convert the value first, as SPOT-RNA's and MultiRM's
  plot flags already did.
- `--pangolin_mask false` stopped the run, as upstream accepts only `True` or `False`; the module now
  takes either value in any case, or a params-file boolean, and passes upstream its spelling.
- MultiRM stopped with a TypeError on any window holding a 3-mer outside its vocabulary (any letter
  but A, C, G, T or U, and some 3-mers with N). Such windows now get `NA` scores and no site calls,
  with a warning per sequence; the other windows score as before (identical output on the test data).
- RhoFold+ took the GPU whenever `/dev/nvidia0` existed, which Singularity also shows to the CPU image
  on a GPU node; upstream then failed on every sequence and the task on its missing output. The
  wrapper now asks PyTorch whether CUDA works.
- `--utrlm_checkpoint` loaded a checkpoint whose tensor names did not match the model without an error
  and predicted from random weights. The run now stops unless every model tensor loads (six tensors
  that every bundled checkpoint holds and the model does not use are allowed), which also catches a
  checkpoint fine-tuned for another `--utrlm_task`. Predictions with the bundled weights are unchanged.
- RiboNN fine-tuning: `--ribonn_finetune_folds 1` ended in a bare numpy error and now stops with a
  message (at least 2 folds); torch is seeded (42) as well as numpy, so the new head's initialization
  repeats; and both training phases use the GPU under `-profile gpu` (PyTorch Lightning 1.8 trains on
  the CPU unless told otherwise).
- RiboTIE: the module replaced the config's `h5_path` and `out_prefix` lines but did not add them,
  so a config without `h5_path` stopped RiboTIE with a TypeError in `process_seq_data`. The module
  now adds both lines when the config has none.
- Fine-tuning heads: for classification the validation rows are now drawn per class, so every class
  with two or more rows is in both training and validation. A random split could leave validation
  with one class and no AUROC, as in all eight runs of `test_finetune_classify`. `metrics.json` writes
  a metric that cannot be computed as `null` instead of `NaN`, which strict JSON readers reject.
  Regression splits are unchanged.

### Documentation
- The model pages and the general pages were checked against the v1.0.2 images by running their CPU
  examples, and corrected. They describe how to run the images directly with Singularity, the
  installation page names release 1.0.2 and its pinned config, and the structure model is called
  RhoFold+, its published name.

## 1.0.2 (2026-11-01)

### Fixed
- ERNIE-RNA returned its second layer, not its last: the wrapper passed `layer_idx=1`, which
  upstream's `ErnieRNAOnestage` reads as an index into its 12 layer outputs (0 is the first;
  12 returns all of them). Sequence embeddings, the CLS token and per-token outputs now come from
  the last layer (`layer_idx=11`), checked against the encoder's final hidden state. Embeddings
  from earlier releases differ and should be recomputed.
- HydraRNA read every U and T of its input as an unknown token: the wrapper turned T into U, but
  HydraRNA's dictionary spells RNA with T (A, T, G, C, N and IUPAC codes; no U), so each U was
  encoded as `<unk>`. The wrapper now turns U into T, as upstream's own example does, and the
  model sees all four bases. Embeddings from earlier releases differ from the corrected ones and
  should be recomputed.
- RiboNN fine-tuning stopped at the start of the second cross-validation fold, with
  `ValueError: too many values to unpack (expected 2)` in upstream RiboNN's `validation_step`.
  The wrapper predicted each held-out fold through upstream's `predict_dataloader()`, which also
  clears the data module's target column, so from the second fold on every batch came without
  its targets. The wrapper now predicts the held-out fold from the test loader, which leaves
  the target column in place. It also switches the model back to eval mode before predicting:
  Lightning's `trainer.test()` returns the model in training mode, and held-out predictions made
  with dropout on did not reproduce the fold's own test metrics. On the test data, the metrics
  of `predictions.tsv` now match the test metrics that each fold logs. The two-phase transfer
  learning itself is unchanged.
- UTR-LM fine-tuning failed at the first batch with `ValueError: not enough values to unpack
  (expected 4, got 2)`: the wrapper gave UTR-LM's batch converter two fields per sequence, but
  the converter reads the four that UTR-LM's `FastaBatchedDataset` yields. The wrapper now
  builds each batch through `FastaBatchedDataset`, unmasked, as upstream's fine-tuning does.
- `--utrlm_finetune_pretrained` with one of the pretraining checkpoints in
  `/opt/utrlm/Model/Pretrained/` loaded none of its weights (0 of 121 tensors) and still logged
  them as loaded: the wrapper matched the file's tensor names against the whole predictor, in
  which the backbone's names carry an `esm2.` prefix. Such a file now loads into the backbone;
  whole-predictor checkpoints load as before. The log reports how many tensors loaded, and the
  run stops with an error before training when any backbone tensor does not load.
- Orthrus stopped before running whenever neither `--orthrus_annotation` nor `--orthrus_gtf`
  was given, which is the default, with `input file name collision -- There are multiple input
  files for each of the following file names: NO_FILE`: the workflow gave both optional inputs
  the same placeholder. Each now has its own (`assets/NO_FILE`, `assets/NO_FILE_GTF`). The GPU
  test profile, which runs Orthrus without either file, failed the same way.
- ERNIE-RNA's memory under the CPU profile grew by about 18 MiB per sequence (20 GB for 1,000
  sequences of 512 nt, against 2.4 GB for 10): on the CPU, `.cpu()` returns the same tensor,
  so each stored embedding was a numpy view that kept its sequence's whole model output
  alive. The wrapper now copies the 768 values. On 300 sequences the peak fell from 7.3 GB to
  2.4 GB with identical embeddings. The GPU profile, where `.cpu()` already copies, was not
  affected.
- Saluki's memory grew by about 5 MiB per sequence under both profiles (6.4 GB of RAM and
  8.9 GB of GPU memory for 1,000 sequences): the wrapper ran Keras `predict()` on one array of
  every input for each of the 50 ensemble members. It now predicts fixed batches of 32,
  Keras' own default, through `predict_on_batch()`, and keeps the encoded inputs as booleans
  until each batch is predicted. For 1,000 sequences on an RTX A5500, GPU memory fell from
  8.9 GB to 1.4 GB and RAM from 6.5 GB to 1.1 GB, at the same speed; on the CPU the
  predictions are identical, and on the GPU they differ by about as much as two runs of the
  released wrapper do (ensemble-mean scores by at most 0.00002).

### Changed
- ERNIE-RNA's sequence embedding is now the last layer averaged over the nucleotides, as for the
  other embedding models. It was the CLS token of the second layer (see Fixed), which records
  mostly the input's first nucleotide (a linear classifier recovers it for all of 5,000 human and
  mouse transcripts). `--ernierna_pooling cls` gives the last layer's CLS token.
- UTR-LM fine-tuning trains as upstream's fine-tuning scripts do (`MJ3_...` for MRL, `MJ4_...`
  for TE and EL). It uses SGD with momentum 0.9 and weight decay 1e-4 instead of Adam, at the
  same default learning rate of 0.01, so `--utrlm_finetune_lr` is now an SGD learning rate. By
  default it starts from the task's pretrained backbone in `/opt/utrlm/Model/Pretrained/`
  instead of random weights: `ESM2SISS_FS4.1_..._epoch93.pkl` for `mrl` and
  `ESM2SI_3.1_..._MLMLossMin.pkl` for `te` and `el`, the files of upstream's README.
  `--utrlm_finetune_pretrained none` keeps random weights. With Adam at 0.01 the predictions
  collapsed to a near-constant value even for a label computed from the sequence (10 times the
  GC fraction of the scored 50 nt: standard deviation 0.0001 against the labels' 0.62); at the
  new defaults the model learns that label (validation Pearson correlation 0.99). The UTR-LM
  page lists where the training still differs from upstream's scripts.
- UTR-LM fine-tuning seeds every random draw with `--utrlm_finetune_seed` (default 1337, the seed
  of upstream's fine-tuning scripts): the train/validation split, the initialization of new
  weights, the batch order and dropout. A run with the same seed, input, CPU model and number of
  CPU threads now repeats exactly. The split follows the seed; it used a fixed seed of 42 before.
- The test profile, and with it the CI pipeline test, runs RiboNN fine-tuning (2 folds, 1 epoch
  per phase) on `tests/data/ribonn_finetune.tsv` and UTR-LM fine-tuning (2 epochs) on
  `tests/data/utrlm_finetune.csv`; the CI step checks their outputs.

### Documentation
- The home page, model overview, fine-tuning guide, quickstart, installation and direct-Docker
  pages were checked against the code and the model pages, corrected and shortened. The
  direct-Docker commands for Saluki, TranslationAI, RiboNN and SPOT-RNA on a GPU were wrong; the
  GPU-only models are Orthrus, HydraRNA and DRfold2.
- The RiboNN and UTR-LM pages, the fine-tuning guide, the quickstart and the model overview no
  longer say that RiboNN and UTR-LM fine-tuning fail. The UTR-LM page describes the starting
  weights and the choices of `--utrlm_finetune_pretrained`, and where the fine-tuning still
  differs from upstream's scripts.
- Removed the benchmark page and its weekly workflow, which had been disabled after 16 failed runs.

### Added
- `conf/containers_v1.0.1.config` pins every image to its v1.0.1 registry digest; pass it with
  `nextflow -c` to run exactly the release images. `scripts/pin_container_digests.py` now writes
  each choice between the CPU and GPU image as a closure: written as a plain expression, a config
  given with `-c` picked the GPU images even under `-profile cpu`.

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
- UTR-LM scored sequences in length-sorted batches but wrote the scores in input order, so when
  inputs differed in length after cropping (shorter than 50 nt for MRL, 100 nt for TE and EL)
  sequences received other sequences' scores. Scores are now written back to their own
  sequences (checked against one-sequence runs). Inputs that are all at least 50 nt (MRL) or
  100 nt (TE, EL) long were not affected.
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
- The 23 model pages were checked claim by claim against the code, the model registry and each
  paper, corrected where they were wrong, and rewritten shorter with the same sections.
- Correction to 1.0.0: staging the reference FASTA's `.fai` helps SpliceAI only. Pangolin reads
  the FASTA through pyfastx, which builds its own index.

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
