#!/usr/bin/env python3
"""
UTR-LM fine-tuning wrapper.
Fine-tunes pretrained UTR-LM model on user-provided 5'UTR expression data
(MRL, TE, or EL) for a new dataset or condition.

Input: CSV/TSV with columns: name, utr (5'UTR sequence), <label_column> (numeric target)
Output: fine-tuned model checkpoint + predictions on held-out test set
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from esm.data import Alphabet
from esm.model.esm2_secondarystructure import ESM2 as ESM2_SISS
from esm.model.esm2_supervised import ESM2 as ESM2_SI
from torch.utils.data import DataLoader, Dataset

LAYERS = 6
HEADS = 16
EMBED_DIM = 128


class CNNLinear(nn.Module):
    """Downstream predictor: ESM2 backbone + FC head."""

    def __init__(self, esm2_cls, alphabet, nodes=40, dropout3=0.5, inp_len=50):
        super().__init__()
        self.inp_len = inp_len
        self.esm2 = esm2_cls(
            num_layers=LAYERS, embed_dim=EMBED_DIM,
            attention_heads=HEADS, alphabet=alphabet,
        )
        self.dropout3 = nn.Dropout(dropout3)
        self.relu = nn.ReLU()
        self.flatten = nn.Flatten()
        self.fc = nn.Linear(in_features=EMBED_DIM, out_features=nodes)
        self.output = nn.Linear(in_features=nodes, out_features=1)

    def forward(self, tokens):
        x = self.esm2(
            tokens, [LAYERS], need_head_weights=False,
            return_contacts=False, return_representation=True,
        )
        x = x["representations"][LAYERS][:, 0]  # CLS token
        x_o = x.unsqueeze(2)
        x = self.flatten(x_o)
        o = self.output(self.dropout3(self.relu(self.fc(x))))
        return o


class UTRDataset(Dataset):
    """Simple dataset: sequences + labels."""

    def __init__(self, sequences, labels, alphabet, max_len):
        self.sequences = [s[-max_len:] for s in sequences]
        self.labels = labels
        self.alphabet = alphabet

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx]

    def collate(self, batch):
        seqs, labels = zip(*batch, strict=True)
        # Use alphabet batch converter (returns 6 items)
        bc = self.alphabet.get_batch_converter()
        dummy_labels = list(range(len(seqs)))
        result = bc(list(zip(dummy_labels, seqs, strict=True)))
        tokens = result[3]  # index 3 = tokens
        return tokens, torch.tensor(labels, dtype=torch.float32)


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune UTR-LM on user expression data"
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="CSV/TSV with columns: name, utr, <label_column>",
    )
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--label", required=True,
        help="Column name containing target values (MRL/TE/EL)",
    )
    parser.add_argument(
        "--task", default="mrl", choices=["mrl", "te", "el"],
        help="Task type (determines backbone + input length). Default: mrl",
    )
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs")
    parser.add_argument("--patience", type=int, default=20, help="Early stopping patience")
    parser.add_argument("--lr", type=float, default=0.01, help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--val-frac", type=float, default=0.2, help="Validation fraction")
    parser.add_argument(
        "--pretrained",
        default=None,
        help="Path to pretrained checkpoint to initialize from (optional)",
    )
    parser.add_argument(
        "--model-dir", default="/opt/utrlm/Model",
        help="Path to Model directory",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)

    os.makedirs(args.output, exist_ok=True)

    # Determine task params
    if args.task == "mrl":
        esm2_cls = ESM2_SISS
        inp_len = 50
        dropout3 = 0.5
    else:
        esm2_cls = ESM2_SI
        inp_len = 100
        dropout3 = 0.2

    # Load data
    sep = "\t" if args.input.endswith(".tsv") else ","
    df = pd.read_csv(args.input, sep=sep)
    df = df.dropna(subset=[args.label])
    sequences = df["utr"].str.upper().str.replace("U", "T", regex=False).tolist()
    labels = df[args.label].astype(float).tolist()
    print(f"Loaded {len(sequences)} sequences", file=sys.stderr)

    # Train/val split
    n = len(sequences)
    n_val = max(1, int(n * args.val_frac))
    indices = np.random.RandomState(42).permutation(n)
    val_idx = indices[:n_val]
    train_idx = indices[n_val:]

    alphabet = Alphabet(standard_toks="AGCT", mask_prob=0.0)

    train_ds = UTRDataset(
        [sequences[i] for i in train_idx],
        [labels[i] for i in train_idx],
        alphabet, inp_len,
    )
    val_ds = UTRDataset(
        [sequences[i] for i in val_idx],
        [labels[i] for i in val_idx],
        alphabet, inp_len,
    )

    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True, collate_fn=train_ds.collate
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False, collate_fn=val_ds.collate
    )

    # Build model
    model = CNNLinear(esm2_cls, alphabet, nodes=40, dropout3=dropout3, inp_len=inp_len).to(device)

    # Optionally load pretrained weights
    if args.pretrained:
        state = torch.load(args.pretrained, map_location=device, weights_only=False)
        state = {k.replace("module.", ""): v for k, v in state.items()}
        model.load_state_dict(state, strict=False)
        print(f"Loaded pretrained weights from {args.pretrained}", file=sys.stderr)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.HuberLoss()

    best_val_loss = float("inf")
    patience_counter = 0
    best_path = os.path.join(args.output, "best_model.pt")

    for epoch in range(args.epochs):
        # Train
        model.train()
        train_loss = 0
        for tokens, targets in train_loader:
            tokens = tokens.to(device)
            targets = targets.to(device)
            preds = model(tokens).squeeze(-1)
            loss = loss_fn(preds, targets)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(targets)
        train_loss /= len(train_ds)

        # Validate
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for tokens, targets in val_loader:
                tokens = tokens.to(device)
                targets = targets.to(device)
                preds = model(tokens).squeeze(-1)
                val_loss += loss_fn(preds, targets).item() * len(targets)
        val_loss /= len(val_ds)

        if (epoch + 1) % 10 == 0:
            print(
                f"  Epoch {epoch + 1}/{args.epochs}  "
                f"train_loss={train_loss:.4f}  val_loss={val_loss:.4f}",
                file=sys.stderr,
            )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), best_path)
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"  Early stopping at epoch {epoch + 1}", file=sys.stderr)
                break

    # Reload best and predict on full dataset
    model.load_state_dict(torch.load(best_path, map_location=device, weights_only=True))
    model.eval()

    full_ds = UTRDataset(sequences, labels, alphabet, inp_len)
    full_loader = DataLoader(
        full_ds, batch_size=args.batch_size, shuffle=False, collate_fn=full_ds.collate
    )

    all_preds = []
    with torch.no_grad():
        for tokens, _ in full_loader:
            tokens = tokens.to(device)
            preds = model(tokens).squeeze(-1)
            all_preds.extend(preds.cpu().numpy().tolist())

    # Save predictions
    df["predicted"] = all_preds
    pred_path = os.path.join(args.output, "predictions.tsv")
    df.to_csv(pred_path, sep="\t", index=False)

    print(f"Done. Best model saved to {best_path}", file=sys.stderr)
    print(f"Predictions written to {pred_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
