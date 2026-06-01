#!/usr/bin/env python3
"""
CLI wrapper for HydraRNA embedding extraction.
Takes a FASTA of RNA sequences, outputs per-sequence (and optionally
per-token) embeddings using the HydraRNA base model (1024-d).

Sequences longer than 10240 nt are split into 10240-nt chunks; the
final embedding is the mean over chunk embeddings.
"""

import argparse
import os
import sys

import numpy as np
import torch
from fairseq import checkpoint_utils, data, options, tasks

WEIGHTS_PATH = "/opt/hydrarna_weights/HydraRNA_model.pt"
DICT_PATH = "/opt/hydrarna_weights/dict"
CHUNK_SIZE = 10240


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


def load_model():
    parser = options.get_generation_parser(default_task="masked_lm_span")
    args = options.parse_args_and_arch(parser, [DICT_PATH])
    task = tasks.setup_task(args)
    print(f"| loading model from {WEIGHTS_PATH}", file=sys.stderr)
    models, _ = checkpoint_utils.load_model_ensemble([WEIGHTS_PATH], task=task)
    return models[0], task


def embed_sequence(model, task, seq, device):
    """Return mean-pooled 1024-d embedding; chunks sequences > CHUNK_SIZE."""
    seq = seq.upper().replace("T", "U")
    chunks = [
        seq[i - CHUNK_SIZE: i]
        for i in range(CHUNK_SIZE, len(seq) + CHUNK_SIZE, CHUNK_SIZE)
    ]
    chunk_vecs = []
    for chunk in chunks:
        tokenized = "<s> " + " ".join(list(chunk))
        tokens = task.source_dictionary.encode_line(tokenized, add_if_not_exist=False)
        batch = data.monolingual_dataset.collate(
            samples=[{"id": -1, "source": tokens, "target": tokens}],
            pad_idx=task.source_dictionary.pad(),
            eos_idx=task.source_dictionary.eos(),
        )
        src = batch["net_input"]["src_tokens"].to(device)
        with torch.no_grad():
            features = model.encoder.extract_features(src_tokens=src)
            # features[0]: (1, L+2, 1024) — strip BOS/EOS, mean over positions
            vec = features[0][:, 1:-1, :].mean(dim=1)  # (1, 1024)
        chunk_vecs.append(vec.float().cpu())
    return torch.stack(chunk_vecs).mean(dim=0).squeeze(0).numpy()  # (1024,)


def main():
    ap = argparse.ArgumentParser(
        description="Extract HydraRNA sequence embeddings from a FASTA file"
    )
    ap.add_argument("-i", "--input", required=True, help="Input FASTA")
    ap.add_argument("-o", "--output", required=True, help="Output directory")
    ap.add_argument(
        "--per-token", action="store_true",
        help="Also save per-token embeddings (L x 1024 .npy per sequence; "
             "first 10240 nt only for sequences that are longer)",
    )
    ap.add_argument(
        "--max-len", type=int, default=10000,
        help="Warn when a sequence exceeds this length (default: 10000)",
    )
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)
    if device.type != "cuda":
        print(
            "Warning: HydraRNA uses Mamba CUDA kernels; CPU inference is not supported.",
            file=sys.stderr,
        )

    model, task = load_model()
    model = model.to(device).half().eval()

    os.makedirs(args.output, exist_ok=True)

    sequences = list(parse_fasta(args.input))
    if not sequences:
        print("Error: no sequences found in input", file=sys.stderr)
        sys.exit(1)

    long_count = sum(1 for _, s in sequences if len(s) > args.max_len)
    if long_count:
        print(f"Note: {long_count} sequences exceed {args.max_len} nt", file=sys.stderr)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    all_embs, all_labels = [], []
    for header, seq in sequences:
        emb = embed_sequence(model, task, seq, device)
        all_embs.append(emb)
        all_labels.append(header)

        if args.per_token:
            chunk = seq.upper().replace("T", "U")[:CHUNK_SIZE]
            tokenized = "<s> " + " ".join(list(chunk))
            tokens = task.source_dictionary.encode_line(tokenized, add_if_not_exist=False)
            batch = data.monolingual_dataset.collate(
                samples=[{"id": -1, "source": tokens, "target": tokens}],
                pad_idx=task.source_dictionary.pad(),
                eos_idx=task.source_dictionary.eos(),
            )
            src = batch["net_input"]["src_tokens"].to(device)
            with torch.no_grad():
                features = model.encoder.extract_features(src_tokens=src)
                token_embs = features[0][:, 1:-1, :].squeeze(0).float().cpu().numpy()
            safe = header.replace("/", "_").replace(" ", "_")
            np.save(os.path.join(args.output, f"{safe}_tokens.npy"), token_embs)

    embeddings = np.stack(all_embs)  # (N, 1024)
    np.save(os.path.join(args.output, "sequence_embeddings.npy"), embeddings)
    with open(os.path.join(args.output, "labels.txt"), "w") as f:
        f.writelines(f"{lbl}\n" for lbl in all_labels)

    print(
        f"Done. Saved {len(all_labels)} embeddings "
        f"(shape: {embeddings.shape}) to {args.output}/",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
