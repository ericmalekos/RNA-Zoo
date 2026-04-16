"""
Minimal Python reproduction of the predict() checkpoint loading bug in
transcript_transformer v1.1.1 (TRISTAN/RiboTIE).

This does NOT require data/BAMs — it reproduces the bug purely by
loading the bundled pretrained checkpoints the same way predict() does.

Run inside the TRISTAN Docker image or any env with transcript_transformer==1.1.1:

    docker run --rm ghcr.io/ericmalekos/rnazoo-tristan:latest \
        /opt/conda/envs/tristan/bin/python /work/reproduce_minimal.py

Or locally:

    pip install transcript_transformer==1.1.1
    python reproduce_minimal.py
"""

import traceback
from importlib.resources import files

import torch
from transcript_transformer.models import TranscriptSeqRiboEmb


def find_checkpoint(subdir, pattern):
    """Find a bundled pretrained checkpoint."""
    pkg = files("transcript_transformer.pretrained").joinpath(subdir)
    for f in pkg.iterdir():
        if str(f).endswith(".ckpt") and pattern in str(f):
            return str(f)
    raise FileNotFoundError(f"No checkpoint matching '{pattern}' in {subdir}")


# -----------------------------------------------------------------------
# Bug A: tt checkpoints have use_ribo=False saved in hparams.
#         predict() doesn't override it → model built without scalar_emb
#         → AttributeError at inference when batch contains ribo data.
# -----------------------------------------------------------------------
print("=" * 70)
print("BUG A: tt checkpoint loaded without use_ribo override")
print("=" * 70)

tt_ckpt = find_checkpoint("tt_models", "Homo_sapiens.GRCh38.113_f0")
print(f"Checkpoint: {tt_ckpt}")

# Inspect what's saved
ckpt_data = torch.load(tt_ckpt, map_location="cpu", weights_only=False)
hp = ckpt_data["hyper_parameters"]
print(f"Saved hparams: use_ribo={hp['use_ribo']}, use_seq={hp['use_seq']}")
print()

# This is exactly what predict() does (transcript_transformer.py line ~163):
print("Loading checkpoint the way predict() does (no use_ribo/use_seq override)...")
try:
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
    print(f"Model loaded. Has scalar_emb: {hasattr(model, 'scalar_emb')}")

    # Simulate what happens at inference when batch has ribo data:
    # parse_embeddings() checks "ribo" in batch.keys()
    # then calls self.scalar_emb(counts) — which doesn't exist.
    print("Trying to access model.scalar_emb (as parse_embeddings would)...")
    _ = model.scalar_emb  # This raises AttributeError
except AttributeError as e:
    print(f"\n>>> FAILS: {e}")
    print(">>> Root cause: checkpoint has use_ribo=False, predict() doesn't override")
    print(">>> The model was built without ribo embedding layers, but inference")
    print(">>> data contains 'ribo' key → parse_embeddings tries self.scalar_emb")
except Exception as e:
    print(f"\n>>> Unexpected error: {e}")
    traceback.print_exc()

# Now show that train() does it correctly:
print()
print("For comparison, train() passes use_ribo=True — this works:")
model = TranscriptSeqRiboEmb.load_from_checkpoint(
    tt_ckpt,
    strict=False,
    use_seq=True,
    use_ribo=True,  # ← This is what predict() is missing
    lr=0.001,
    decay_rate=0.96,
    warmup_step=1500,
    max_seq_len=30000,
    mlm=False,
    mask_frac=0.85,
    rand_frac=0.15,
)
print(f"Model loaded. Has scalar_emb: {hasattr(model, 'scalar_emb')}")


# -----------------------------------------------------------------------
# Bug B: rt checkpoints are from Lightning 1.7.7 with old hparam names
#         (x_ribo/x_seq instead of use_ribo/use_seq) and are missing
#         use_ribo/use_seq entirely → TypeError on instantiation.
# -----------------------------------------------------------------------
print()
print("=" * 70)
print("BUG B: rt checkpoint missing use_ribo/use_seq hparams entirely")
print("=" * 70)

rt_ckpt = find_checkpoint("rt_models", "50perc_06_23_f0")
print(f"Checkpoint: {rt_ckpt}")

ckpt_data = torch.load(rt_ckpt, map_location="cpu", weights_only=False)
hp = ckpt_data["hyper_parameters"]
print(f"Lightning version in checkpoint: {ckpt_data.get('pytorch-lightning_version')}")
print(f"Has 'use_ribo': {'use_ribo' in hp}")
print(f"Has 'use_seq': {'use_seq' in hp}")
print(f"Has old-style 'x_ribo': {'x_ribo' in hp}")
print(f"Has old-style 'x_seq': {'x_seq' in hp}")
print()

print("Loading checkpoint the way predict() does...")
try:
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
except TypeError as e:
    print(f"\n>>> FAILS: {e}")
    print(">>> Root cause: checkpoint was saved with Lightning 1.7.7 using")
    print(">>> old hparam names (x_ribo/x_seq). Current __init__ expects")
    print(">>> use_ribo/use_seq as required positional args, which are absent.")
except Exception as e:
    print(f"\n>>> Unexpected error: {e}")
    traceback.print_exc()


# -----------------------------------------------------------------------
# Proposed fix
# -----------------------------------------------------------------------
print()
print("=" * 70)
print("PROPOSED FIX")
print("=" * 70)
print("""
In transcript_transformer.py, the predict() function (line ~163) loads
checkpoints without passing use_seq/use_ribo:

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

It should match what train() does (line ~37) and include:

        use_seq=args.use_seq,
        use_ribo=args.use_ribo,

For the rt checkpoints (Lightning 1.7.7), the on_load_checkpoint hook
should also migrate x_ribo/x_seq → use_ribo/use_seq.
""")
