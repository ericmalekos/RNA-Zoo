#!/usr/bin/env python3
"""
CLI wrapper for MultiRM RNA modification site prediction.
Takes a FASTA of RNA sequences (>=51 nt), predicts 12 RNA modification types per position.
"""

import argparse
import os
import pickle
import sys

import numpy as np
import pandas as pd
import torch
from torch import nn

RMS = ["Am", "Cm", "Gm", "Um", "m1A", "m5C", "m5U", "m6A", "m6Am", "m7G", "Psi", "AtoI"]
NUM_TASK = 12
WINDOW = 51


# ---- Model components (adapted from upstream for CPU/GPU compatibility) ----


class BahdanauAttention(nn.Module):
    def __init__(self, in_features, hidden_units, num_task):
        super().__init__()
        self.W1 = nn.Linear(in_features=in_features, out_features=hidden_units)
        self.W2 = nn.Linear(in_features=in_features, out_features=hidden_units)
        self.V = nn.Linear(in_features=hidden_units, out_features=num_task)

    def forward(self, hidden_states, values):
        hidden_with_time_axis = torch.unsqueeze(hidden_states, dim=1)
        score = self.V(nn.Tanh()(self.W1(values) + self.W2(hidden_with_time_axis)))
        attention_weights = nn.Softmax(dim=1)(score)
        values = torch.transpose(values, 1, 2)
        context_vector = torch.matmul(values, attention_weights)
        context_vector = torch.transpose(context_vector, 1, 2)
        return context_vector, attention_weights


class EmbeddingSeq(nn.Module):
    def __init__(self, weight_dict_path):
        super().__init__()
        weight_dict = pickle.load(open(weight_dict_path, "rb"))  # noqa: SIM115
        weights = torch.FloatTensor(list(weight_dict.values()))
        num_embeddings = len(list(weight_dict.keys()))
        embedding_dim = 300
        self.embedding = nn.Embedding(
            num_embeddings=num_embeddings, embedding_dim=embedding_dim
        )
        self.embedding.weight = nn.Parameter(weights)
        self.embedding.weight.requires_grad = False

    def forward(self, x):
        return self.embedding(x.long())


class MultiRMModel(nn.Module):
    def __init__(self, num_task, embedding_path):
        super().__init__()
        self.num_task = num_task
        self.embed = EmbeddingSeq(embedding_path)
        self.NaiveBiLSTM = nn.LSTM(
            input_size=300, hidden_size=256, batch_first=True, bidirectional=True
        )
        self.Attention = BahdanauAttention(
            in_features=512, hidden_units=100, num_task=num_task
        )
        for i in range(num_task):
            setattr(
                self,
                f"NaiveFC{i}",
                nn.Sequential(
                    nn.Linear(in_features=512, out_features=128),
                    nn.ReLU(),
                    nn.Dropout(),
                    nn.Linear(in_features=128, out_features=1),
                    nn.Sigmoid(),
                ),
            )

    def forward(self, x):
        x = self.embed(x)
        batch_size = x.size()[0]
        output, (h_n, c_n) = self.NaiveBiLSTM(x)
        h_n = h_n.view(batch_size, output.size()[-1])
        context_vector, attention_weights = self.Attention(h_n, output)
        outs = []
        for i in range(self.num_task):
            fc_layer = getattr(self, f"NaiveFC{i}")
            y = fc_layer(context_vector[:, i, :])
            y = torch.squeeze(y, dim=-1)
            outs.append(y)
        return outs


# ---- Utility functions ----


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


def word2index(my_dict):
    return {ele: idx for idx, ele in enumerate(my_dict.keys())}


def seq2index(seqs, my_dict, window=3):
    """Convert RNA sequences to k-mer index arrays."""
    w2i = word2index(my_dict)
    temp = []
    for seq in seqs:
        kmers = [seq[i : i + window] for i in range(len(seq) - window + 1)]
        indices = [w2i.get(k) for k in kmers]
        temp.append(indices)
    return np.array(temp)


def main():
    parser = argparse.ArgumentParser(
        description="Predict RNA modification sites with MultiRM (12 modification types)"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="FASTA file of RNA sequences (min 51 nt)"
    )
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance threshold for calling modifications (default: 0.05)",
    )
    parser.add_argument(
        "--weights",
        default="/opt/multirm/Weights/MultiRM/trained_model_51seqs.pkl",
        help="Path to model weights",
    )
    parser.add_argument(
        "--embeddings",
        default="/opt/multirm/Embeddings/embeddings_12RM.pkl",
        help="Path to word2vec embeddings",
    )
    parser.add_argument(
        "--neg-prob",
        default="/opt/multirm/Scripts/neg_prob.csv",
        help="Path to null distribution CSV",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)

    print("Loading MultiRM model...", file=sys.stderr)
    embeddings_dict = pickle.load(open(args.embeddings, "rb"))  # noqa: SIM115
    model = MultiRMModel(num_task=NUM_TASK, embedding_path=args.embeddings).to(device)
    state_dict = torch.load(args.weights, map_location=device, weights_only=False)
    model.load_state_dict(state_dict, strict=False)
    model.eval()

    neg_prob = pd.read_csv(args.neg_prob, header=None, index_col=0)

    os.makedirs(args.output, exist_ok=True)

    # Load sequences
    sequences = []
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("U", "T")
        if len(seq) < WINDOW:
            print(
                f"Warning: {header} ({len(seq)} nt) is shorter than {WINDOW} nt, skipping",
                file=sys.stderr,
            )
            continue
        sequences.append((header, seq))

    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    # Write results
    scores_file = os.path.join(args.output, "modification_scores.tsv")
    sites_file = os.path.join(args.output, "predicted_sites.tsv")

    with (
        open(scores_file, "w") as sf,
        open(sites_file, "w") as pf,
    ):
        sf.write("header\tposition\tbase\t" + "\t".join(RMS) + "\n")
        pf.write("header\tmodification\tposition\tbase\tprobability\tp_value\n")

        for idx, (header, seq) in enumerate(sequences):
            check_pos = len(seq) - WINDOW + 1
            probs = np.zeros((NUM_TASK, check_pos))

            with torch.no_grad():
                for pos in range(check_pos):
                    window_seq = seq[pos : pos + WINDOW]
                    kmers_idx = seq2index([window_seq], embeddings_dict)
                    x = torch.transpose(
                        torch.from_numpy(kmers_idx), 0, 1
                    ).to(device)
                    y_preds = model(x)
                    for k in range(NUM_TASK):
                        probs[k, pos] = y_preds[k].detach().cpu().numpy()[0]

            # Write per-position probabilities (center position of each window)
            for pos in range(check_pos):
                center = pos + 25  # 0-indexed center of 51-nt window
                vals = "\t".join(f"{probs[k, pos]:.6f}" for k in range(NUM_TASK))
                sf.write(f"{header}\t{center + 1}\t{seq[center]}\t{vals}\n")

            # Compute p-values and write significant sites
            for pos in range(check_pos):
                center = pos + 25
                for k in range(NUM_TASK):
                    p_val = np.sum(neg_prob.iloc[k, :] > probs[k, pos]) / len(
                        neg_prob.iloc[k, :]
                    )
                    if p_val < args.alpha:
                        pf.write(
                            f"{header}\t{RMS[k]}\t{center + 1}\t{seq[center]}\t"
                            f"{probs[k, pos]:.6f}\t{p_val:.6f}\n"
                        )

            print(
                f"  [{idx + 1}/{len(sequences)}] {header} ({len(seq)} nt)",
                file=sys.stderr,
            )

    print(f"Done. Results written to {args.output}/", file=sys.stderr)


if __name__ == "__main__":
    main()
