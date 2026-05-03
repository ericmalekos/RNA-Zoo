#!/usr/bin/env python3
"""
CLI wrapper for mRNABERT embedding extraction.
Takes a FASTA of mRNA sequences, auto-detects the longest ORF in each
(per upstream `data_process/process_pretrain_data.py`), formats input as
single-letter UTR tokens + 3-letter CDS codon tokens, and emits per-sequence
(and optionally per-token) embeddings.

mRNABERT is a 12-layer / 768-dim MosaicBERT pretrained on ~18M full-length
mRNAs with hybrid per-nt-UTR / per-codon-CDS tokenization (74-token vocab)
and ALiBi positional embeddings (length-extrapolation). License: Apache-2.0.
"""

import argparse
import os
import sys

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer
from transformers.models.bert.configuration_bert import BertConfig

WEIGHTS_PATH = "/opt/mrnabert_weights"
HIDDEN_DIM = 768
MAX_TOKENS = 1024  # tokenizer model_max_length; ALiBi extrapolates beyond config max_pos=512


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


def find_longest_cds(seq):
    """Find longest ORF (ATG...STOP) in DNA sequence. Mirrors upstream
    data_process/process_pretrain_data.py:find_longest_cds. Returns
    (start, end) 0-based inclusive of the stop-codon end, or None."""
    stops = {"TAG", "TAA", "TGA"}
    best = None  # (start, end)
    start = seq.find("ATG")
    while start != -1:
        end = start + 3
        while end < len(seq):
            codon = seq[end:end + 3]
            if codon in stops and (end - start) % 3 == 0:
                cds_end = end + 2
                if best is None or (cds_end - start) > (best[1] - best[0]):
                    best = (start, cds_end)
                break
            end += 1
        start = seq.find("ATG", start + 1)
    return best


def split_with_cds(seq, cds_range):
    """Tokenize: single-letter for non-CDS, 3-letter codons for CDS.
    Returns list of token strings. cds_range is (start, end) 0-based
    inclusive or None."""
    if cds_range is None:
        return list(seq)
    start, end = cds_range
    tokens = list(seq[:start])
    cds = seq[start:end + 1]
    tokens.extend(cds[i:i + 3] for i in range(0, len(cds), 3))
    tokens.extend(list(seq[end + 1:]))
    return tokens


def main():
    parser = argparse.ArgumentParser(
        description="Extract mRNABERT embeddings from mRNA sequences (auto ORF detection)"
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="FASTA file of mRNA sequences (DNA: A/C/G/T or RNA: A/C/G/U)",
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output directory for embedding files"
    )
    parser.add_argument(
        "--per-token",
        action="store_true",
        help="Save per-token embeddings (T x 768 .npy per sequence; T = tokens incl CLS+SEP)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=MAX_TOKENS,
        help=f"Maximum token count per sequence after CLS/SEP (default: {MAX_TOKENS}). "
             "Longer inputs are truncated.",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)

    print(f"Loading mRNABERT model from {WEIGHTS_PATH}...", file=sys.stderr)
    # Match upstream README recipe — load stock BertConfig (not the trust_remote_code
    # custom config class) and pass it to AutoModel. Without the explicit config,
    # AutoModel raises a config_class mismatch error because the trust_remote_code
    # path registers BertModel with the upstream-vendored BertConfig while transformers
    # expects the stock one.
    config = BertConfig.from_pretrained(WEIGHTS_PATH)
    tokenizer = AutoTokenizer.from_pretrained(WEIGHTS_PATH)
    model = AutoModel.from_pretrained(
        WEIGHTS_PATH, trust_remote_code=True, config=config
    ).eval().to(device)

    os.makedirs(args.output, exist_ok=True)

    formatted = []
    cds_info = []  # for logging
    skipped = 0
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("U", "T")
        if not seq:
            print(f"Warning: {header} has empty sequence, skipping", file=sys.stderr)
            skipped += 1
            continue

        cds_range = find_longest_cds(seq)
        tokens = split_with_cds(seq, cds_range)
        # Truncate to max_tokens (CLS + SEP take 2 slots, so keep max-2 tokens)
        if len(tokens) > args.max_tokens - 2:
            tokens = tokens[: args.max_tokens - 2]
            print(
                f"Warning: {header} truncated to {args.max_tokens - 2} tokens",
                file=sys.stderr,
            )

        formatted.append((header, " ".join(tokens)))
        if cds_range is None:
            cds_info.append((header, "no ORF detected — treated as all-UTR"))
        else:
            start1 = cds_range[0] + 1
            end1 = cds_range[1] + 1
            cds_info.append(
                (header, f"ORF at {start1}-{end1} (1-based, len={end1 - start1 + 1})")
            )

    if not formatted:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    for label, info in cds_info:
        print(f"  {label}: {info}", file=sys.stderr)
    print(f"Processing {len(formatted)} sequences...", file=sys.stderr)

    all_seq_embeddings = []
    all_labels = []

    for header, spaced in formatted:
        encoded = tokenizer(
            spaced, padding=False, truncation=False, return_tensors="pt"
        )
        input_ids = encoded["input_ids"].to(device)
        attn_mask = encoded["attention_mask"].to(device)

        with torch.no_grad():
            out = model(input_ids=input_ids, attention_mask=attn_mask)

        # last_hidden_state: (1, T, 768) where T = #tokens incl CLS/SEP
        token_embeddings = out.last_hidden_state if hasattr(out, "last_hidden_state") else out[0]

        # Mean-pool excluding CLS at pos 0 and SEP at last non-pad position.
        pool_mask = attn_mask.clone()
        pool_mask[:, 0] = 0  # exclude CLS
        last_nonpad = attn_mask.sum(dim=1) - 1  # (1,)
        for b, idx in enumerate(last_nonpad):
            pool_mask[b, idx] = 0  # exclude SEP

        masked = token_embeddings * pool_mask.unsqueeze(-1).float()
        denom = pool_mask.sum(dim=1, keepdim=True).float().clamp(min=1.0)
        seq_emb = (masked.sum(dim=1) / denom).squeeze(0).cpu().numpy()  # (768,)
        all_seq_embeddings.append(seq_emb)
        all_labels.append(header)

        if args.per_token:
            tok_emb = token_embeddings.squeeze(0).cpu().numpy()  # (T, 768)
            safe_name = header.replace("/", "_").replace(" ", "_")
            np.save(os.path.join(args.output, f"{safe_name}_tokens.npy"), tok_emb)

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
