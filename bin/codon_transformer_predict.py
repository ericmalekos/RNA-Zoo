#!/usr/bin/env python3
"""
CLI wrapper for CodonTransformer codon optimization.
Takes a FASTA of amino acid sequences + organism name, outputs optimized DNA sequences.
"""

import argparse
import sys

import torch
from CodonTransformer.CodonPrediction import predict_dna_sequence
from transformers import AutoTokenizer, BigBirdForMaskedLM


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


def main():
    parser = argparse.ArgumentParser(
        description="Optimize codon sequences using CodonTransformer"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="FASTA file of amino acid sequences"
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output FASTA file of optimized DNA sequences"
    )
    parser.add_argument(
        "--organism",
        default="Homo sapiens",
        help="Target organism name (default: 'Homo sapiens')",
    )
    # Use BooleanOptionalAction so users can pass --deterministic or --no-deterministic;
    # the previous declaration was action="store_true" + default=True, which made the
    # flag a no-op (it could never set the value False).
    parser.add_argument(
        "--deterministic",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use deterministic decoding (default: on; pass --no-deterministic to sample)",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)

    print("Loading CodonTransformer model...", file=sys.stderr)
    tokenizer = AutoTokenizer.from_pretrained("adibvafa/CodonTransformer")
    model = BigBirdForMaskedLM.from_pretrained("adibvafa/CodonTransformer").to(device)

    with open(args.output, "w") as out_f:
        for header, protein_seq in parse_fasta(args.input):
            print(f"Optimizing: {header}", file=sys.stderr)
            output = predict_dna_sequence(
                protein=protein_seq,
                organism=args.organism,
                device=device,
                tokenizer=tokenizer,
                model=model,
                attention_type="original_full",
                deterministic=args.deterministic,
            )
            dna_seq = output.predicted_dna
            out_f.write(f">{header}\n{dna_seq}\n")

    print(f"Results written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
