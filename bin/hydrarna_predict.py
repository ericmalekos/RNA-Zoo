#!/usr/bin/env python3
"""
CLI wrapper for HydraRNA embedding extraction.

HydraRNA is a 12-layer hybrid Hydra-SSM (Mamba-style state-space model) +
2 attention layers, pretrained on ~73M ncRNAs and ~22M protein-coding mRNAs
with the masked_lm_span task in fairseq. Supports up to 10K nt at inference.

License: MIT (upstream LICENSE; copyright header reads "GPL" but body is
unambiguous MIT terms).

Loading mirrors upstream `examples/extract_HydraAttRNA12_5UTRMRL.py`:
- fairseq's `checkpoint_utils.load_model_ensemble` with the masked_lm_span task
- character-level tokenization with `<s> ` BOS prefix and space-separated nts
- model.encoder.extract_features → (1, N+2, 1024) tensor; pool across positions
  excluding the BOS and EOS tokens, average over chunks for sequences > 10K nt.
"""

import argparse
import os
import sys

import numpy as np
import torch
from fairseq import checkpoint_utils, data, options, tasks

WEIGHTS_PATH = os.environ.get("HYDRARNA_WEIGHTS", "/opt/hydrarna_weights/HydraRNA_model.pt")
DICT_DIR = os.environ.get("HYDRARNA_DICT", "/opt/hydrarna_repo/dict")
HIDDEN_DIM = 1024
CHUNK_SIZE = 10240  # max input length per inference chunk (per upstream)


def parse_fasta(path):
    header, seq_parts = None, []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(seq_parts)
                header = line[1:]
                seq_parts = []
            elif line:
                seq_parts.append(line)
    if header is not None:
        yield header, "".join(seq_parts)


def main():
    parser = argparse.ArgumentParser(
        description="Extract HydraRNA embeddings from RNA sequences"
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="FASTA file of RNA sequences (A/C/G/U or A/C/G/T; T converted to internal alphabet)",
    )
    parser.add_argument(
        "-o", "--output", required=True,
        help="Output directory for embedding files",
    )
    parser.add_argument(
        "--per-token",
        action="store_true",
        help="Save per-token embeddings (N+2 x 1024 .npy per sequence; "
             "includes BOS+EOS positions). For sequences > 10K nt, only "
             "the last chunk's per-token embedding is saved.",
    )
    parser.add_argument(
        "--no-half",
        action="store_true",
        help="Disable model.half() — use full float32 precision (default uses fp16 like upstream)",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)

    print(f"Loading HydraRNA from {WEIGHTS_PATH} (dict: {DICT_DIR})...", file=sys.stderr)
    parser_fs = options.get_generation_parser(default_task="masked_lm_span")
    fs_args = options.parse_args_and_arch(parser_fs, [DICT_DIR])
    task = tasks.setup_task(fs_args)
    models, _model_args = checkpoint_utils.load_model_ensemble([WEIGHTS_PATH], task=task)
    model = models[0].to(device).eval()
    if not args.no_half and device.type == "cuda":
        model.half()

    # Flash-Attention 2.x requires Ampere GPUs (compute capability ≥ 8.0).
    # On Turing (RTX 20xx, GTX 16xx) the flash kernels fail with
    # "FlashAttention only supports Ampere GPUs or newer". HydraRNA's
    # mha.py ships a non-flash SelfAttention class with the same forward
    # signature; swap the inner_attn modules and clear the use_flash_attn
    # flag so the parent MHA's forward path skips flash-specific kwargs.
    # Patch is idempotent on Ampere+ (just slightly slower attention).
    if device.type == "cuda":
        from fairseq.models.hydraAttRNA.mha import FlashSelfAttention, SelfAttention
        for module in model.modules():
            inner = getattr(module, "inner_attn", None)
            if isinstance(inner, FlashSelfAttention):
                replacement = SelfAttention(
                    causal=inner.causal,
                    softmax_scale=inner.softmax_scale,
                    attention_dropout=inner.drop.p if hasattr(inner, "drop") else 0.0,
                )
                module.inner_attn = replacement.to(device)
                if hasattr(module, "use_flash_attn"):
                    module.use_flash_attn = False

    os.makedirs(args.output, exist_ok=True)

    sequences = []
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("U", "T")  # match upstream alphabet (DNA-style)
        if not seq:
            print(f"Warning: {header} has empty sequence, skipping", file=sys.stderr)
            continue
        sequences.append((header, seq))

    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    all_seq_embeddings = []
    all_labels = []

    for header, seq in sequences:
        # Chunk for >10K nt sequences (upstream does the same).
        seq_chunks = [seq[i:i + CHUNK_SIZE] for i in range(0, len(seq), CHUNK_SIZE)]
        # Upstream prepends '<s> ' and space-separates each char.
        formatted = ["<s> " + " ".join(list(c)) for c in seq_chunks]
        tokens_chunks = [
            task.source_dictionary.encode_line(line, add_if_not_exist=False)
            for line in formatted
        ]
        batch = data.monolingual_dataset.collate(
            samples=[{"id": -1, "source": tokens, "target": tokens} for tokens in tokens_chunks],
            pad_idx=task.source_dictionary.pad(),
            eos_idx=task.source_dictionary.eos(),
        )
        src_tokens = batch["net_input"]["src_tokens"].to(device)

        with torch.no_grad():
            y = model.encoder.extract_features(src_tokens=src_tokens)
            # y[0]: (n_chunks, chunk_len + 2, 1024)
            tok_emb = y[0].float()  # cast back to fp32 for numpy
            # Mean over positions [1:-1] (excludes BOS and EOS), then mean over chunks.
            chunk_means = tok_emb[:, 1:-1, :].mean(dim=1)  # (n_chunks, 1024)
            seq_emb = chunk_means.mean(dim=0).cpu().numpy()  # (1024,)

        all_seq_embeddings.append(seq_emb)
        all_labels.append(header)

        if args.per_token:
            # Save the last chunk's per-token embedding (N+2, 1024) — full
            # per-token output for chunked sequences would conflate multiple chunks.
            tok_np = tok_emb[-1].cpu().numpy()
            safe_name = header.replace("/", "_").replace(" ", "_")
            np.save(os.path.join(args.output, f"{safe_name}_tokens.npy"), tok_np)

    seq_embeddings = np.stack(all_seq_embeddings)  # (N, 1024)
    np.save(os.path.join(args.output, "sequence_embeddings.npy"), seq_embeddings)

    with open(os.path.join(args.output, "labels.txt"), "w") as f:
        for label in all_labels:
            f.write(label + "\n")

    print(
        f"Done. Saved {len(all_labels)} sequence embeddings "
        f"(shape: {seq_embeddings.shape}) to {args.output}/",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
