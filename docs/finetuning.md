# Fine Tuning

RNAZoo exposes a generic **head trainer** that fits a small head (linear / MLP / XGBoost) on top of frozen embeddings from any of the 9 foundation models — the standard "linear probe" pattern from foundation-model literature, extended with non-linear options.

Three model-specific fine-tunes — [RiboNN](models/RiboNN.md#fine-tuning-on-your-own-data), [UTR-LM](models/UTRLM.md#fine-tuning-on-your-own-data), and [RiboTIE](models/RiboTIE.md) — use their own custom training loops (not the head trainer) and are documented on their model pages. This page is about the head trainer.

## Supported foundation models

| Model | Embed dim | CPU image |
|-------|-----------|-----------|
| [RNA-FM](models/RNAFM.md) | 640 | yes |
| [RiNALMo](models/RiNALMo.md) | 1280 | yes (slow) |
| [ERNIE-RNA](models/ERNIERNA.md) | 768 | single image |
| [Orthrus](models/Orthrus.md) | 512 | GPU-only inference; CPU fine-tune via embeddings shortcut |
| [RNAErnie](models/RNAErnie.md) | 768 | yes |
| [PlantRNA-FM](models/PlantRNAFM.md) | 480 | yes |
| [CaLM](models/CaLM.md) | 768 | yes |
| [mRNABERT](models/mRNABERT.md) | 768 | yes |
| [HydraRNA](models/HydraRNA.md) | 1024 | GPU-only inference; CPU fine-tune via embeddings shortcut |

## Quick start

```bash
# Regression on RNA-FM with the default linear head
nextflow run main.nf -profile docker,cpu \
  --rnafm_finetune_input my_labels.tsv \
  --rnafm_finetune_label te
```

Outputs in `results/rnafm_finetune/rnafm_finetune_out/`:
- `best_head.pt` — trained head + config
- `predictions.tsv` — per-row predictions (train/val split annotated)
- `metrics.json` — MSE, R², Pearson r, Spearman r (regression) or accuracy / F1 / AUROC / confusion matrix (classification)

Replace `rnafm` with any other foundation-model prefix (`rinalmo`, `ernierna`, `orthrus`, `rnaernie`, `plantrnafm`, `calm`, `mrnabert`, `hydrarna`) — the rest of the interface is identical.

## Input format

TSV (default) or CSV with a header row. Required columns: `name`, `sequence`, and the label column (configurable via `--<model>_finetune_label`):

```
name<TAB>sequence<TAB>te
seq_001<TAB>GGGUGCGAU...<TAB>1.42
seq_002<TAB>AUUCCGAGA...<TAB>0.87
...
```

Labels can be:
- **Numeric** — treated as regression by default.
- **Integer with ≤ 10 unique values** — auto-detected as classification.
- **Strings** (e.g. `high`, `low`) — always classification; encoded internally with a stable sort order.

Override auto-detection with `--<model>_finetune_task regression|classification`.

## Two execution paths

### Path A: full chain (default)

Predict + head training happen in one Nextflow process inside the model's existing inference image:

```bash
nextflow run main.nf -profile docker,cpu \
  --rnafm_finetune_input my_labels.tsv \
  --rnafm_finetune_label te
```

The backbone runs once per training session — fine if you're only fine-tuning once. Supports `--<model>_finetune_head_type linear|mlp` (XGBoost requires Path B).

### Path B: precomputed embeddings (shortcut)

If you've already cached embeddings (e.g., from a prior inference run), feed the `.npy` directly:

```bash
# 1. (One-time) Compute embeddings via the inference workflow
nextflow run main.nf -profile docker,cpu \
  --rnafm_input my_seqs.fa \
  --outdir results_emb

# 2. Re-use those embeddings for any number of fine-tune sessions
nextflow run main.nf -profile docker,cpu \
  --rnafm_finetune_input my_labels.tsv \
  --rnafm_finetune_label te \
  --rnafm_finetune_embeddings results_emb/rnafm/rnafm_out/sequence_embeddings.npy
```

When `--<model>_finetune_embeddings` is set, the workflow skips `<model>_predict.py` and runs head training in the dedicated `rnazoo-finetune-head` image (CPU, ~1.9 GB). Supports all three head types.

Side benefit: Orthrus and HydraRNA fine-tunes via Path B no longer require a GPU — head training is CPU and the dedicated image doesn't need the model's CUDA stack.

Embedding row order **must** match TSV row order. The head trainer exits with an error if shapes disagree. The `sequence` column in the TSV is optional and ignored when `_embeddings` is set.

## Head types

Set via `--<model>_finetune_head_type`. Default is `linear`.

| Type | Architecture | Approx params (D=640) | When to use |
|------|--------------|-----------------------|-------------|
| `linear` (default) | `nn.Linear(D, out_dim)` | ~640 | Canonical representation-quality probe. Forces the comparison to be about backbone embeddings, not head capacity. Best when you want numbers that reflect the foundation model. |
| `mlp` | `Linear(D, 64) → ReLU → Dropout(0.2) → Linear(64, out_dim)` | ~41K | Non-linear interactions in the embedding space. Need a few hundred labeled examples to avoid overfitting. The default before 2026-05-03. |
| `xgboost` | `XGBRegressor` / `XGBClassifier`, 200 trees, depth=6 | tree ensemble | Small labeled datasets (≤ ~few hundred examples). Tree ensembles often beat small MLPs on small-n tabular data. **Path B only** (requires the dedicated `rnazoo-finetune-head` image). |

Backward compat: to reproduce numbers from before 2026-05-03, pass `--<model>_finetune_head_type mlp`.

## Regression vs. classification

| Aspect | Regression | Classification |
|--------|------------|----------------|
| Loss | MSE (torch heads) / RMSE (XGBoost) | Cross-entropy / log-loss |
| Output | Single float per row | Argmax class + per-class probabilities |
| Metrics | MSE, R², Pearson r, Spearman r | Accuracy, macro/weighted F1, AUROC (binary), confusion matrix, per-class precision/recall |
| Label scaling | Mean/std normalization on train split (auto-inverted at predict time) | LabelEncoder; mapping saved in checkpoint |

`--<model>_finetune_task` accepts `auto`, `regression`, or `classification`. Auto-detection rules:

- All values parse as float and have > 10 unique values → **regression**
- Values are integer-valued with ≤ 10 unique values, **or** any string label → **classification**

## Outputs

Whichever path and head type you pick, the output directory schema is the same:

```
results/<model>_finetune/<model>_finetune_out/
├── predictions.tsv      # per-row predictions
├── metrics.json         # split metrics (overall / train / val)
└── best_head.{pt,ubj}   # torch state_dict (linear/mlp) or XGBoost UBJSON
```

For XGBoost there's also `best_head_config.json` with the head config (head type, task, embed dim, class names) so the model can be reloaded standalone.

`predictions.tsv` columns:

- **Regression:** `name`, `true`, `predicted`, `split`
- **Classification:** `name`, `true`, `predicted`, `prob_<class_0>`, …, `prob_<class_K-1>`, `split`

`split` is `train` or `val` per the deterministic 80/20 split (`--<model>_finetune_val_frac` to adjust).

## Worked example: mRNA stability bin classification

Realistic scenario: you have a wet-lab dataset of mRNAs with measured half-lives and want a binary high-vs-low stability classifier for screening new designs. Bin classification is more robust than continuous regression on noisy stability proxies.

```bash
# 1. (One-time) Compute embeddings via the inference workflow
nextflow run main.nf -profile docker,cpu \
  --mrnabert_input my_seqs.fa \
  --outdir results_emb

# 2. labels TSV: name + sequence + binary "stability" column
# name      sequence    stability
# tx_001    AUGCC...    high
# tx_002    AUGGG...    low
# ...

# 3. Fine-tune an XGBoost classifier on the cached embeddings
nextflow run main.nf -profile docker,cpu \
  --mrnabert_finetune_input my_labels.tsv \
  --mrnabert_finetune_label stability \
  --mrnabert_finetune_embeddings results_emb/mrnabert/mrnabert_out/sequence_embeddings.npy \
  --mrnabert_finetune_head_type xgboost \
  --mrnabert_finetune_task classification
```

Result: `results/mrnabert_finetune/mrnabert_finetune_out/` with `best_head.ubj`, `predictions.tsv` (per-row class + probabilities), `metrics.json` (accuracy, macro F1, AUROC, confusion matrix).

## Other classification tasks well-suited to RNAZoo

- **ncRNA type** (multi-class: miRNA / snoRNA / lncRNA / tRNA / rRNA / snRNA) — standard rep-quality benchmark in foundation-model papers; lets users reproduce paper-style numbers on their own data.
- **Coding vs. non-coding** (binary) — de novo annotation; the LncRNA-BERT motivation.
- **mRNA subcellular localization** (multi-class) — cytoplasm / nucleus / ER / mitochondria.
- **TE tertile (high / mid / low)** — more robust than continuous TE prediction on sparse ribo-seq data.

## Common parameters

Each foundation model uses the same set of flags, with a per-model prefix. For RNA-FM the flags are `--rnafm_finetune_*`; substitute the prefix for any other model.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--<model>_finetune_input` | `null` | TSV/CSV with `name`, `sequence` (optional under Path B), `<label_col>` |
| `--<model>_finetune_label` | `null` (required) | Column name with target values |
| `--<model>_finetune_embeddings` | `null` | Path to precomputed `(N, D)` `.npy`; switches to Path B |
| `--<model>_finetune_head_type` | `linear` | `linear`, `mlp`, or `xgboost` (xgboost requires `_embeddings`) |
| `--<model>_finetune_task` | `auto` | `auto`, `regression`, or `classification` |
| `--<model>_finetune_epochs` | 20 | Max epochs for torch heads (early-stop patience 5; ignored by XGBoost) |
| `--<model>_finetune_lr` | 1e-3 | Adam learning rate (torch) or XGBoost learning rate |
| `--<model>_finetune_outdir` | `<outdir>/<model>_finetune` | Output directory override |

For each foundation model's specific flag names, see its model page (linked at the top).

## Opt-in test profiles

Three test profiles exercise the head trainer end-to-end on a 30-sequence GC-correlated fixture:

```bash
# All 9 models, full chain (Path A), linear head, regression
nextflow run . -profile test_finetune,docker,cpu

# All 9 models, embeddings shortcut (Path B), linear head, regression
# Uses tests/data/foundation_finetune_emb.npy (random 30×256 fixture)
nextflow run . -profile test_finetune_from_emb,docker,cpu

# All 9 models, classification (Path B), linear head, 2-class GC bin labels
nextflow run . -profile test_finetune_classify,docker,cpu
```

The smokes verify wiring + finite metrics, not learning quality (the embeddings fixture is random, so val Pearson r / accuracy is meaningless).

## Limitations

- **Backbone fine-tuning is out of scope** for the head trainer. Frozen-backbone only. UTR-LM is the one foundation-adjacent model with backbone fine-tuning exposed (separate workflow on its model page).
- **XGBoost full-chain is rejected** — running XGBoost requires the `rnazoo-finetune-head` image, which doesn't ship the model backbones. If you set `--<model>_finetune_head_type xgboost` without `--<model>_finetune_embeddings`, the workflow errors and points you at Path B.
- **Multi-label classification not supported** — single-label only (one class per row). Tasks like multi-label GO term prediction would need a separate code path.
- **No imbalanced-class handling** — pre-balance your training data, or accept that `weighted_f1` will reflect the imbalance.
- **No hyperparameter sweeping** — defaults only. Run multiple invocations with different `--<model>_finetune_lr` / `_epochs` for ad-hoc sweeps.
- **No embedding-dim validation** — the head trainer adapts its input layer to whatever `(N, D)` shape it sees. If you accidentally feed a 640-dim file thinking it's RNA-FM's output but actually point at the RNAErnie alias (which expects 768-dim *from the model* — but the head doesn't know that), the head will train fine. The mismatch is harmless because the head only ever sees the cached `.npy`.

## Model-specific fine-tuning workflows (not the head trainer)

These three models have custom fine-tuning pipelines that don't use `bin/finetune_head.py`. They live on their respective model pages:

- **[RiboNN](models/RiboNN.md#fine-tuning-on-your-own-data)** — transfer learning for translation-efficiency prediction. Two-phase training (frozen conv layers → full model) with K-fold cross-validation. Inputs are 4-column UTR/CDS/UTR + target tables, not the unified TSV format.
- **[UTR-LM](models/UTRLM.md#fine-tuning-on-your-own-data)** — full ESM2 backbone fine-tuning on user MRL/TE/EL data. Saves a checkpoint that can be passed back into prediction via `--utrlm_checkpoint`.
- **[RiboTIE](models/RiboTIE.md)** — built-in: every prediction run automatically fine-tunes the pretrained transformer on the user's ribo-seq BAMs before scoring ORFs. Controlled via `--ribotie_max_epochs` and `--ribotie_patience`.
