# `predict()` fails to load pretrained checkpoints — missing `use_seq`/`use_ribo` overrides

## Summary

`predict()` in `transcript_transformer.py` does not pass `use_seq` and `use_ribo` to `load_from_checkpoint()`, causing inference to fail with **both** bundled checkpoint types (`tt` and `rt`) when using the `trained_model` config path (i.e., prediction without fine-tuning first).

The `train()` function correctly passes these arguments (line ~37), but `predict()` (line ~163) omits them.

## Scope — what is and isn't affected

The README-documented invocations work correctly:
- `tis_transformer config.yml --model human` (and `--fasta` variant) — verified working
- `ribotie config.yml` — verified working (Lightning auto-migrates the rt checkpoint hparams during the fine-tuning step)

The bug only manifests when the user supplies a **hand-written `trained_model:` block** in the YAML pointing at a bundled `tt`/`rt` checkpoint, which causes `predict()` to reload from checkpoint without first going through `train()`. This is an uncommon path but valid (e.g., a user who wants to skip fine-tuning and run inference directly from the bundled checkpoints).

## Versions

- `transcript_transformer`: 1.1.1 (pip install)
- `pytorch_lightning`: 2.6.1
- `torch`: 2.6.0

## Two failure modes

### Bug A: `tt` checkpoints → `AttributeError: 'TranscriptSeqRiboEmb' object has no attribute 'scalar_emb'`

The `tt` pretrained checkpoints (e.g., `Homo_sapiens.GRCh38.113_f0.tt.ckpt`) were trained on sequence only, so they have `use_ribo=False` saved in their hyperparameters. When `predict()` loads them without overriding `use_ribo=True`, the model is instantiated without the ribo embedding layers (`scalar_emb`, `ribo_count_emb`, `ribo_read_emb`). At inference time, when the data batch contains ribo-seq counts, `parse_embeddings()` tries to access `self.scalar_emb` and fails.

**Traceback:**
```
File "transcript_transformer/models.py", line 144, in parse_embeddings
    xs.append(self.scalar_emb(counts) * self.ribo_count_emb.weight)
AttributeError: 'TranscriptSeqRiboEmb' object has no attribute 'scalar_emb'
```

### Bug B: `rt` checkpoints → `TypeError: missing 2 required positional arguments: 'use_seq' and 'use_ribo'`

The `rt` pretrained checkpoints (e.g., `50perc_06_23_f0.rt.ckpt`) were saved with PyTorch Lightning 1.7.7 using old hyperparameter names (`x_ribo`/`x_seq` instead of `use_ribo`/`use_seq`). When `predict()` loads them, `load_from_checkpoint` cannot find the required `use_seq` and `use_ribo` constructor arguments.

**Traceback:**
```
File "transcript_transformer/models.py", in __init__
TypeError: TranscriptSeqRiboEmb.__init__() missing 2 required positional arguments: 'use_seq' and 'use_ribo'
```

## Minimal reproduction (no data needed)

Save as `reproduce.py` and run with `pip install transcript_transformer==1.1.1`:

```python
import torch
from importlib.resources import files
from transcript_transformer.models import TranscriptSeqRiboEmb

# --- Bug A: tt checkpoint ---
tt_ckpt = str(
    files("transcript_transformer.pretrained.tt_models")
    .joinpath("Homo_sapiens.GRCh38.113_f0.tt.ckpt")
)

# This is what predict() does (transcript_transformer.py ~line 163):
model = TranscriptSeqRiboEmb.load_from_checkpoint(
    tt_ckpt,
    map_location=torch.device("cpu"),
    strict=False,
    max_seq_len=30000,
    mlm=False,
    mask_frac=0.85,
    rand_frac=0.15,
    metrics=[],
)
print(f"Has scalar_emb: {hasattr(model, 'scalar_emb')}")  # False
model.scalar_emb  # AttributeError


# --- Bug B: rt checkpoint ---
rt_ckpt = str(
    files("transcript_transformer.pretrained.rt_models")
    .joinpath("50perc_06_23_f0.rt.ckpt")
)

# Same predict() call — fails with TypeError
model = TranscriptSeqRiboEmb.load_from_checkpoint(
    rt_ckpt,
    map_location=torch.device("cpu"),
    strict=False,
    max_seq_len=30000,
    mlm=False,
    mask_frac=0.85,
    rand_frac=0.15,
    metrics=[],
)
```

## Root cause

In `transcript_transformer.py`, `predict()` loads the checkpoint like this:

```python
# transcript_transformer.py, ~line 163
model = TranscriptSeqRiboEmb.load_from_checkpoint(
    args.transfer_checkpoint,
    map_location=map_location,
    strict=False,
    max_seq_len=args.max_seq_len,
    mlm=False,
    mask_frac=0.85,
    rand_frac=0.15,
    metrics=[],
)
```

But `train()` in the same file correctly passes `use_seq` and `use_ribo`:

```python
# transcript_transformer.py, ~line 37
model = TranscriptSeqRiboEmb.load_from_checkpoint(
    args.transfer_checkpoint,
    strict=False,
    use_seq=args.use_seq,
    use_ribo=args.use_ribo,
    lr=args.lr,
    decay_rate=args.decay_rate,
    warmup_step=args.warmup_steps,
    max_seq_len=args.max_seq_len,
    mlm=args.mlm,
    mask_frac=args.mask_frac,
    rand_frac=args.rand_frac,
)
```

## Suggested fix

**For Bug A:** Add `use_seq=args.use_seq, use_ribo=args.use_ribo` to the `load_from_checkpoint` call in `predict()`:

```python
# transcript_transformer.py, predict() function
model = TranscriptSeqRiboEmb.load_from_checkpoint(
    args.transfer_checkpoint,
    map_location=map_location,
    strict=False,
    use_seq=args.use_seq,        # ← add
    use_ribo=args.use_ribo,      # ← add
    max_seq_len=args.max_seq_len,
    mlm=False,
    mask_frac=0.85,
    rand_frac=0.15,
    metrics=[],
)
```

**For Bug B:** Add a hyperparameter migration in `on_load_checkpoint` to handle old `x_ribo`/`x_seq` names:

```python
# models.py, TranscriptSeqRiboEmb.on_load_checkpoint()
def on_load_checkpoint(self, checkpoint):
    # Migrate old hparam names from Lightning 1.7.7 checkpoints
    hp = checkpoint.get("hyper_parameters", {})
    if "x_ribo" in hp and "use_ribo" not in hp:
        hp["use_ribo"] = hp.pop("x_ribo")
    if "x_seq" in hp and "use_seq" not in hp:
        hp["use_seq"] = hp.pop("x_seq")
    # ... existing migration code ...
```

## Impact

This means the `trained_model` config path (using pre-computed checkpoints for prediction without fine-tuning) is broken in v1.1.1. The fine-tuning path (`train()` → `predict()` with a model object) still works because `predict()` receives the already-constructed model and doesn't need to load from checkpoint.
