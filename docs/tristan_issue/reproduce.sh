#!/usr/bin/env bash
# ============================================================================
# Minimal reproduction of TRISTAN v1.1.1 predict() checkpoint bugs
# Requires: docker with ghcr.io/ericmalekos/rnazoo-tristan:latest
#           (or: pip install transcript_transformer==1.1.1)
# ============================================================================
set -euo pipefail

WORKDIR="$(mktemp -d)"
echo "Working in: $WORKDIR"

# --- Step 1: Extract bundled test data -------
docker run --rm -v "$WORKDIR:/out" ghcr.io/ericmalekos/rnazoo-tristan:latest bash -c "
  cp /opt/TRISTAN/tests/data/GRCh38v110_snippet.fa   /out/
  cp /opt/TRISTAN/tests/data/GRCh38v110_snippet.gtf   /out/
  cp /opt/TRISTAN/tests/data/SRR000001.bam             /out/
  cp /opt/TRISTAN/tests/data/SRR000002.bam             /out/
  cp /opt/TRISTAN/tests/data/SRR000003.bam             /out/
"

# --- Step 2: Write config using tt (trained_model) checkpoints -------
cat > "$WORKDIR/config_tt.yml" << 'YAML'
fa_path: GRCh38v110_snippet.fa
gtf_path: GRCh38v110_snippet.gtf

ribo_paths:
  "1": SRR000001.bam
  "2": SRR000002.bam
  "3": SRR000003.bam

h5_path: out/ribotie.h5
out_prefix: out/ribotie

trained_model:
  folds:
    0:
      test: []
      train: ['2']
      transfer_checkpoint: /opt/conda/envs/tristan/lib/python3.10/site-packages/transcript_transformer/pretrained/tt_models/Homo_sapiens.GRCh38.113_f0.tt.ckpt
      val: ['3']
    1:
      test: ['3']
      train: ['1']
      transfer_checkpoint: /opt/conda/envs/tristan/lib/python3.10/site-packages/transcript_transformer/pretrained/tt_models/Homo_sapiens.GRCh38.113_f1.tt.ckpt
      val: ['2']
YAML

# --- Step 3: Write config using rt (pretrained_model) checkpoints -------
cat > "$WORKDIR/config_rt.yml" << 'YAML'
fa_path: GRCh38v110_snippet.fa
gtf_path: GRCh38v110_snippet.gtf

ribo_paths:
  "1": SRR000001.bam
  "2": SRR000002.bam
  "3": SRR000003.bam

h5_path: out/ribotie.h5
out_prefix: out/ribotie

trained_model:
  folds:
    0:
      test: []
      train: ['2']
      transfer_checkpoint: /opt/conda/envs/tristan/lib/python3.10/site-packages/transcript_transformer/pretrained/rt_models/50perc_06_23_f0.rt.ckpt
      val: ['3']
    1:
      test: ['3']
      train: ['1']
      transfer_checkpoint: /opt/conda/envs/tristan/lib/python3.10/site-packages/transcript_transformer/pretrained/rt_models/50perc_06_23_f1.rt.ckpt
      val: ['2']
YAML

echo ""
echo "======================================================================"
echo "BUG A: tt checkpoints → AttributeError: no attribute 'scalar_emb'"
echo "======================================================================"
echo ""
docker run --rm -v "$WORKDIR:/work" -w /work \
  ghcr.io/ericmalekos/rnazoo-tristan:latest \
  bash -c "mkdir -p out && ribotie config_tt.yml --accelerator cpu --overwrite_data --max_epochs 2 --patience 1" \
  2>&1 || true

echo ""
echo "======================================================================"
echo "BUG B: rt checkpoints → TypeError: missing 'use_seq' and 'use_ribo'"
echo "======================================================================"
echo ""
docker run --rm -v "$WORKDIR:/work" -w /work \
  ghcr.io/ericmalekos/rnazoo-tristan:latest \
  bash -c "mkdir -p out && ribotie config_rt.yml --accelerator cpu --overwrite_data --max_epochs 2 --patience 1" \
  2>&1 || true

echo ""
echo "Working directory preserved at: $WORKDIR"
