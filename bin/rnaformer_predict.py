#!/usr/bin/env python3
"""
CLI wrapper for RNAformer RNA secondary structure prediction.
Takes a FASTA of RNA sequences, outputs base-pair matrices and dot-bracket structures.
"""

import argparse
import os
import sys

import loralib as lora
import numpy as np
import torch
from RNAformer.model.RNAformer import RiboFormer
from RNAformer.utils.configuration import Config

SEQ_VOCAB = ["A", "C", "G", "U", "N"]
SEQ_STOI = dict(zip(SEQ_VOCAB, range(len(SEQ_VOCAB)), strict=True))


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


def insert_lora_layer(model, ft_config):
    """Insert LoRA layers into the model (required for finetuned checkpoints)."""
    lora_config = {
        "r": ft_config.r,
        "lora_alpha": ft_config.lora_alpha,
        "lora_dropout": ft_config.lora_dropout,
    }
    with torch.no_grad():
        for name, _module in model.named_modules():
            if any(rk in name for rk in ft_config.replace_layer):
                parent = model.get_submodule(".".join(name.split(".")[:-1]))
                target_name = name.split(".")[-1]
                target = model.get_submodule(name)
                if isinstance(target, torch.nn.Linear) and "qkv" in name:
                    new_module = lora.MergedLinear(
                        target.in_features,
                        target.out_features,
                        bias=target.bias is not None,
                        enable_lora=[True, True, True],
                        **lora_config,
                    )
                    new_module.weight.copy_(target.weight)
                    if target.bias is not None:
                        new_module.bias.copy_(target.bias)
                elif isinstance(target, torch.nn.Linear):
                    new_module = lora.Linear(
                        target.in_features,
                        target.out_features,
                        bias=target.bias is not None,
                        **lora_config,
                    )
                    new_module.weight.copy_(target.weight)
                    if target.bias is not None:
                        new_module.bias.copy_(target.bias)
                elif isinstance(target, torch.nn.Conv2d):
                    kernel_size = target.kernel_size[0]
                    new_module = lora.Conv2d(
                        target.in_channels,
                        target.out_channels,
                        kernel_size,
                        padding=(kernel_size - 1) // 2,
                        bias=target.bias is not None,
                        **lora_config,
                    )
                    new_module.conv.weight.copy_(target.weight)
                    if target.bias is not None:
                        new_module.conv.bias.copy_(target.bias)
                setattr(parent, target_name, new_module)
    return model


def pairs_to_dotbracket(pairs, length):
    """Convert list of (i,j) base pairs to dot-bracket notation."""
    structure = ["."] * length
    pk_chars = [("(", ")"), ("[", "]"), ("{", "}")]

    sorted_pairs = sorted(pairs, key=lambda p: p[0])

    levels = [[] for _ in pk_chars]
    for i, j in sorted_pairs:
        for level_idx, level_pairs in enumerate(levels):
            conflict = False
            for pi, pj in level_pairs:
                if (i < pi < j < pj) or (pi < i < pj < j):
                    conflict = True
                    break
            if not conflict:
                level_pairs.append((i, j))
                open_char, close_char = pk_chars[level_idx]
                structure[i] = open_char
                structure[j] = close_char
                break

    return "".join(structure)


def main():
    parser = argparse.ArgumentParser(
        description="Predict RNA secondary structure with RNAformer"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="FASTA file of RNA sequences"
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output directory"
    )
    parser.add_argument(
        "--config",
        default="/opt/rnaformer_models/RNAformer_32M_config_intra_family_finetuned.yml",
        help="Path to model config YAML",
    )
    parser.add_argument(
        "--state-dict",
        default="/opt/rnaformer_models/RNAformer_32M_state_dict_intra_family_finetuned.pth",
        help="Path to model state dict",
    )
    parser.add_argument(
        "--cycling",
        type=int,
        default=6,
        help="Number of recycling steps (default: 6; use 0 to disable)",
    )
    parser.add_argument(
        "--save-matrix",
        action="store_true",
        help="Also save base-pair probability matrices as .npy files",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Generate contact map heatmap PNGs for each sequence",
    )
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}", file=sys.stderr)

    print("Loading RNAformer model...", file=sys.stderr)
    config = Config(config_file=args.config)
    if args.cycling:
        config.RNAformer.cycling = args.cycling

    model = RiboFormer(config.RNAformer)

    if hasattr(config, "lora") and config.lora:
        model = insert_lora_layer(model, config)

    state_dict = torch.load(args.state_dict, map_location=device, weights_only=True)
    model.load_state_dict(state_dict, strict=True)

    if args.cycling and args.cycling > 0:
        model.cycle_steps = args.cycling

    if device == "cuda":
        model = model.cuda()
        if torch.cuda.is_bf16_supported():
            model = model.bfloat16()
        else:
            model = model.half()

    model.eval()

    os.makedirs(args.output, exist_ok=True)

    # Load sequences
    sequences = []
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("T", "U")
        if len(seq) == 0:
            print(f"Warning: {header} has empty sequence, skipping", file=sys.stderr)
            continue
        sequences.append((header, seq))

    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    # Write results
    results_file = os.path.join(args.output, "structures.txt")
    with open(results_file, "w") as out_f:
        for idx, (header, seq) in enumerate(sequences):
            src_seq = torch.LongTensor([SEQ_STOI.get(c, 4) for c in seq])

            with torch.no_grad():
                seq_tensor = src_seq.unsqueeze(0).to(device)
                src_len = torch.LongTensor([len(seq)]).to(device)
                if device == "cuda":
                    dtype = (
                        torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                    )
                    pdb_sample = torch.FloatTensor([[1]]).to(dtype).to(device)
                else:
                    pdb_sample = torch.FloatTensor([[1]]).to(device)

                logits, pair_mask = model(seq_tensor, src_len, pdb_sample)

                prob_matrix = torch.sigmoid(logits[0, :, :, -1]).cpu().numpy()
                pred_mat = prob_matrix > 0.5

            # Extract pairs
            pairs = list(
                set(tuple(sorted(pair)) for pair in np.argwhere(pred_mat == 1))
            )
            pairs.sort()

            # Convert to dot-bracket
            db = pairs_to_dotbracket(pairs, len(seq))

            # Write FASTA-like output
            out_f.write(f">{header}\n{seq}\n{db}\n")

            safe_name = header.replace("/", "_").replace(" ", "_")

            if args.save_matrix:
                np.save(os.path.join(args.output, f"{safe_name}_bpmat.npy"), prob_matrix)

            if args.plot:
                from rnazoo_plots import plot_contact_map

                plot_contact_map(
                    prob_matrix, seq, header,
                    os.path.join(args.output, f"{safe_name}_contact.png"),
                    title_prefix="RNAformer: ",
                )

            print(
                f"  [{idx + 1}/{len(sequences)}] {header} ({len(seq)} nt, {len(pairs)} pairs)",
                file=sys.stderr,
            )

    print(f"Done. Results written to {results_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
