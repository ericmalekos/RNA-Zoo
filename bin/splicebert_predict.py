#!/usr/bin/env python3
"""
CLI wrapper for SpliceBERT embedding extraction.
Takes a FASTA of RNA sequences, outputs per-sequence (and optionally
per-token) embeddings using the SpliceBERT.1024nt checkpoint
(Chen et al., Brief. Bioinform. 2024; weights from Zenodo 7995778).

SpliceBERT is a stock BertForMaskedLM checkpoint, so AutoModel +
AutoTokenizer load it directly. The tokenizer is a BertTokenizer
that expects whitespace-separated DNA letters (U is converted to T
before tokenization). Vocab: [PAD] [UNK] [CLS] [SEP] [MASK] N A C G T.
"""

import argparse
import os
import sys

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

WEIGHTS_PATH = "/opt/splicebert_weights"
HIDDEN_DIM = 512
MAX_RAW_LEN = 1024  # 1026 max-position-embeddings minus CLS + SEP


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
        description="Extract SpliceBERT embeddings from RNA sequences"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="FASTA file of RNA sequences (A/C/G/U/T/N)"
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output directory for embedding files"
    )
    parser.add_argument(
        "--per-token",
        action="store_true",
        help="Save per-token embeddings (L x 512 .npy per sequence) in addition to per-sequence",
    )
    parser.add_argument(
        "--max-len",
        type=int,
        default=MAX_RAW_LEN,
        help=f"Maximum raw sequence length (default: {MAX_RAW_LEN}). SpliceBERT.1024nt "
             "has 1026 max-position-embeddings; CLS+SEP consume 2 slots.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Batch size for inference (default: 8)",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)

    print(f"Loading SpliceBERT model from {WEIGHTS_PATH}...", file=sys.stderr)
    tokenizer = AutoTokenizer.from_pretrained(WEIGHTS_PATH)
    model = AutoModel.from_pretrained(WEIGHTS_PATH).eval().to(device)

    os.makedirs(args.output, exist_ok=True)

    sequences = []
    skipped = 0
    for header, seq in parse_fasta(args.input):
        # SpliceBERT was trained on DNA letters (T, not U). README explicitly
        # instructs replace("U", "T") before tokenization.
        seq = seq.upper().replace("U", "T")
        if not seq:
            print(f"Warning: {header} has empty sequence, skipping", file=sys.stderr)
            skipped += 1
            continue
        if len(seq) > args.max_len:
            print(
                f"Warning: {header} ({len(seq)} nt) exceeds {args.max_len} nt limit, truncating",
                file=sys.stderr,
            )
            seq = seq[: args.max_len]
        sequences.append((header, seq))

    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    all_seq_embeddings = []
    all_labels = []

    for i in range(0, len(sequences), args.batch_size):
        batch = sequences[i : i + args.batch_size]
        batch_labels = [h for h, _ in batch]
        # SpliceBERT BertTokenizer expects whitespace-separated nucleotides.
        batch_seqs_spaced = [" ".join(list(s)) for _, s in batch]

        encoded = tokenizer(
            batch_seqs_spaced, padding=True, truncation=False, return_tensors="pt"
        )
        input_ids = encoded["input_ids"].to(device)
        attn_mask = encoded["attention_mask"].to(device)

        with torch.no_grad():
            out = model(input_ids=input_ids, attention_mask=attn_mask)

        # last_hidden_state: (B, L+2, 512) — pos 0 is [CLS], last
        # non-pad position is [SEP]. Mean-pool over actual sequence
        # positions only (matches RNA-FM / RiNALMo / PlantRNA-FM convention).
        token_embeddings = out.last_hidden_state  # (B, L+2, 512)
        pool_mask = attn_mask.clone()
        pool_mask[:, 0] = 0  # exclude [CLS]
        last_nonpad = attn_mask.sum(dim=1) - 1  # (B,)
        for b, idx in enumerate(last_nonpad):
            pool_mask[b, idx] = 0  # exclude [SEP]

        masked = token_embeddings * pool_mask.unsqueeze(-1).float()
        denom = pool_mask.sum(dim=1, keepdim=True).float().clamp(min=1.0)
        seq_embs = (masked.sum(dim=1) / denom).cpu().numpy()  # (B, 512)

        for j, label in enumerate(batch_labels):
            all_seq_embeddings.append(seq_embs[j])
            all_labels.append(label)

            if args.per_token:
                seq_len = len(batch[j][1])
                tok_emb = token_embeddings[j, 1 : seq_len + 1].cpu().numpy()  # (L, 512)
                safe_name = label.replace("/", "_").replace(" ", "_")
                np.save(os.path.join(args.output, f"{safe_name}_tokens.npy"), tok_emb)

        print(
            f"  Batch {i // args.batch_size + 1}/"
            f"{(len(sequences) + args.batch_size - 1) // args.batch_size} done",
            file=sys.stderr,
        )

    seq_embeddings = np.stack(all_seq_embeddings)  # (N, 512)
    np.save(os.path.join(args.output, "sequence_embeddings.npy"), seq_embeddings)

    with open(os.path.join(args.output, "labels.txt"), "w") as f:
        for label in all_labels:
            f.write(label + "\n")

    print(
        f"Done. Saved {len(all_labels)} sequence embeddings "
        f"(shape: {seq_embeddings.shape}) to {args.output}/",
        file=sys.stderr,
    )
    if skipped:
        print(f"Skipped {skipped} empty sequences.", file=sys.stderr)


if __name__ == "__main__":
    main()
