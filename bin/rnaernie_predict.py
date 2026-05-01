#!/usr/bin/env python3
"""
CLI wrapper for RNAErnie embedding extraction.
Takes a FASTA of RNA sequences, outputs per-sequence (and optionally
per-token) embeddings using the LLM-EDA/RNAErnie HF port (Apache-2.0).

Uses transformers.BertModel directly with a tiny built-in char-level
tokenizer — the RNAErnie vocab is just A/U/C/G/N + 6 special tokens,
so no heavy tokenizer package is needed.
"""

import argparse
import os
import sys

import numpy as np
import torch
from transformers import BertModel

WEIGHTS_PATH = "/opt/rnaernie_weights"
HIDDEN_DIM = 768
MAX_RAW_LEN = 2046  # 2048 max-position-embeddings minus CLS + SEP

# Vocab from LLM-EDA/RNAErnie/vocab.txt
VOCAB = {
    "[PAD]": 0,
    "[UNK]": 1,
    "[CLS]": 2,
    "[EOS]": 3,
    "[SEP]": 4,
    "[MASK]": 5,
    "A": 6,
    "U": 7,
    "C": 8,
    "G": 9,
    "N": 10,
}
PAD_ID = VOCAB["[PAD]"]
UNK_ID = VOCAB["[UNK]"]
CLS_ID = VOCAB["[CLS]"]
SEP_ID = VOCAB["[SEP]"]


def parse_fasta(path):
    """Parse a FASTA file, yielding (header, sequence) tuples."""
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


def encode_batch(seqs):
    """Char-level tokenize a batch of (already-uppercased, U-form) RNA
    sequences. Returns input_ids and attention_mask tensors padded to
    the longest sequence in the batch (length = L+2 to include CLS/SEP).
    """
    encoded = [
        [CLS_ID] + [VOCAB.get(c, UNK_ID) for c in s] + [SEP_ID] for s in seqs
    ]
    max_len = max(len(e) for e in encoded)
    input_ids = torch.full((len(encoded), max_len), PAD_ID, dtype=torch.long)
    attention_mask = torch.zeros((len(encoded), max_len), dtype=torch.long)
    for i, ids in enumerate(encoded):
        input_ids[i, : len(ids)] = torch.tensor(ids, dtype=torch.long)
        attention_mask[i, : len(ids)] = 1
    return input_ids, attention_mask


def main():
    parser = argparse.ArgumentParser(
        description="Extract RNAErnie embeddings from RNA sequences"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="FASTA file of RNA sequences (A/C/G/U)"
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output directory for embedding files"
    )
    parser.add_argument(
        "--per-token",
        action="store_true",
        help="Save per-token embeddings (L x 768 .npy per sequence) in addition to per-sequence",
    )
    parser.add_argument(
        "--max-len",
        type=int,
        default=MAX_RAW_LEN,
        help=f"Maximum raw sequence length (default: {MAX_RAW_LEN}). RNAErnie has a "
             "2048 max-position-embedding limit; CLS+SEP consume 2 slots.",
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

    print(f"Loading RNAErnie model from {WEIGHTS_PATH}...", file=sys.stderr)
    model = BertModel.from_pretrained(WEIGHTS_PATH).eval().to(device)

    os.makedirs(args.output, exist_ok=True)

    sequences = []
    skipped = 0
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("T", "U")
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
        batch_seqs = [s for _, s in batch]

        input_ids, attn_mask = encode_batch(batch_seqs)
        input_ids = input_ids.to(device)
        attn_mask = attn_mask.to(device)

        with torch.no_grad():
            out = model(input_ids=input_ids, attention_mask=attn_mask)

        # last_hidden_state: (B, L+2, 768) — pos 0 is [CLS], last
        # non-pad position is [SEP]. Mean-pool over actual sequence
        # positions only (matches the convention of the other
        # foundation-model wrappers in the zoo).
        token_embeddings = out.last_hidden_state  # (B, L+2, 768)
        pool_mask = attn_mask.clone()
        pool_mask[:, 0] = 0  # exclude CLS
        last_nonpad = attn_mask.sum(dim=1) - 1  # (B,)
        for b, idx in enumerate(last_nonpad):
            pool_mask[b, idx] = 0  # exclude SEP

        masked = token_embeddings * pool_mask.unsqueeze(-1).float()
        denom = pool_mask.sum(dim=1, keepdim=True).float().clamp(min=1.0)
        seq_embs = (masked.sum(dim=1) / denom).cpu().numpy()  # (B, 768)

        for j, label in enumerate(batch_labels):
            all_seq_embeddings.append(seq_embs[j])
            all_labels.append(label)

            if args.per_token:
                seq_len = len(batch_seqs[j])
                tok_emb = token_embeddings[j, 1 : seq_len + 1].cpu().numpy()  # (L, 768)
                safe_name = label.replace("/", "_").replace(" ", "_")
                np.save(os.path.join(args.output, f"{safe_name}_tokens.npy"), tok_emb)

        print(
            f"  Batch {i // args.batch_size + 1}/"
            f"{(len(sequences) + args.batch_size - 1) // args.batch_size} done",
            file=sys.stderr,
        )

    seq_embeddings = np.stack(all_seq_embeddings)  # (N, 768)
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
