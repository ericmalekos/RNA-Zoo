#!/usr/bin/env python3
"""
Generic linear-probe head trainer for foundation-model fine-tuning.

Inputs: numpy embeddings (N, D) + labels.txt (N rows, one float each)
Outputs: best_head.pt (state_dict + config) + predictions.tsv + metrics.json

Used as Step 3 of the foundation-model linear-probe pipeline:
  TSV → [tsv_to_fasta] → FASTA + labels → [predict] → embeddings →
  [this script] → head + predictions

Currently regression-only (the foundation-finetune fixture uses numeric labels;
classification can be added later by the wrapper passing --task classification).

The backbone model is NOT modified or loaded here — this trains a small
MLP on top of pre-computed embeddings. The MLP is the only thing that
changes; backbone weights stay frozen / unloaded.
"""

import argparse
import json
import os
import sys

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


class MLPHead(nn.Module):
    def __init__(self, embed_dim: int, hidden_dim: int = 64, out_dim: int = 1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(embed_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, out_dim),
        )

    def forward(self, x):
        return self.net(x)


def parse_fasta_labels(fasta_path: str):
    """Parse FASTA headers (names) so we can join name → prediction in output."""
    if not fasta_path or not os.path.isfile(fasta_path):
        return None
    names = []
    with open(fasta_path) as f:
        for line in f:
            if line.startswith(">"):
                names.append(line[1:].strip())
    return names


def pearson(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Plain Pearson r without scipy."""
    if y_true.size < 2:
        return float("nan")
    yt = y_true - y_true.mean()
    yp = y_pred - y_pred.mean()
    den = float(np.sqrt((yt * yt).sum() * (yp * yp).sum()))
    if den == 0:
        return float("nan")
    return float((yt * yp).sum() / den)


def spearman(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Plain Spearman r without scipy (rank-then-Pearson)."""
    if y_true.size < 2:
        return float("nan")
    rt = np.argsort(np.argsort(y_true)).astype(float)
    rp = np.argsort(np.argsort(y_pred)).astype(float)
    return pearson(rt, rp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-e", "--embeddings", required=True, help="Path to .npy (N, D)")
    parser.add_argument("-l", "--labels", required=True, help="Path to labels.txt (N rows)")
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--names-fasta", default=None,
        help="Optional FASTA whose headers provide row names for predictions.tsv. "
             "If absent, names are 'row_<i>'.",
    )
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--val-frac", type=float, default=0.2)
    parser.add_argument("--patience", type=int, default=5,
                        help="Early-stopping patience (epochs without val improvement)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    X = np.load(args.embeddings)
    if X.ndim != 2:
        print(f"ERROR: embeddings must be 2D (N,D); got shape {X.shape}", file=sys.stderr)
        sys.exit(1)
    n, d = X.shape

    with open(args.labels) as f:
        y_list = [float(line.strip()) for line in f if line.strip()]
    y = np.asarray(y_list, dtype=np.float32)
    if y.shape[0] != n:
        print(
            f"ERROR: labels rows ({y.shape[0]}) != embeddings rows ({n})",
            file=sys.stderr,
        )
        sys.exit(1)

    names = parse_fasta_labels(args.names_fasta)
    if names is None or len(names) != n:
        names = [f"row_{i}" for i in range(n)]

    # Train/val split (deterministic)
    rng = np.random.RandomState(args.seed)
    idx = rng.permutation(n)
    n_val = max(1, int(round(n * args.val_frac)))
    val_idx = idx[:n_val]
    train_idx = idx[n_val:]
    if train_idx.size < 1:
        # Tiny dataset — train on all, val == train.
        train_idx = idx
        val_idx = idx[:1]

    Xt = torch.from_numpy(X[train_idx]).float()
    yt = torch.from_numpy(y[train_idx]).float().unsqueeze(1)
    Xv = torch.from_numpy(X[val_idx]).float()
    yv = torch.from_numpy(y[val_idx]).float().unsqueeze(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(
        f"head trainer device: {device}; embed_dim={d}, "
        f"n_train={Xt.shape[0]}, n_val={Xv.shape[0]}",
        file=sys.stderr,
    )

    model = MLPHead(embed_dim=d, hidden_dim=args.hidden).to(device)
    opt = optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.MSELoss()

    Xt = Xt.to(device)
    yt = yt.to(device)
    Xv = Xv.to(device)
    yv = yv.to(device)

    # Normalize labels (mean/std) for stable training; un-normalize at predict time.
    label_mean = float(y[train_idx].mean())
    label_std = float(y[train_idx].std()) or 1.0
    yt_norm = (yt - label_mean) / label_std
    yv_norm = (yv - label_mean) / label_std

    best_val_loss = float("inf")
    best_state = None
    epochs_no_improve = 0

    bs = args.batch_size
    for epoch in range(args.epochs):
        model.train()
        # Mini-batch through train set.
        perm = torch.randperm(Xt.shape[0], device=device)
        total_loss = 0.0
        for s in range(0, Xt.shape[0], bs):
            sel = perm[s:s + bs]
            opt.zero_grad()
            pred = model(Xt[sel])
            loss = loss_fn(pred, yt_norm[sel])
            loss.backward()
            opt.step()
            total_loss += float(loss.detach()) * sel.shape[0]
        train_mse = total_loss / Xt.shape[0]

        model.eval()
        with torch.no_grad():
            pv = model(Xv)
            val_loss = float(loss_fn(pv, yv_norm))

        if val_loss < best_val_loss - 1e-6:
            best_val_loss = val_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        print(
            f"epoch {epoch + 1}/{args.epochs}: train_mse(norm)={train_mse:.4f} "
            f"val_mse(norm)={val_loss:.4f} best={best_val_loss:.4f} "
            f"no_improve={epochs_no_improve}",
            file=sys.stderr,
        )
        if epochs_no_improve >= args.patience:
            print(f"early-stop at epoch {epoch + 1}", file=sys.stderr)
            break

    if best_state is None:
        best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    os.makedirs(args.output, exist_ok=True)

    # Save head with config so it can be loaded standalone.
    head_path = os.path.join(args.output, "best_head.pt")
    torch.save(
        {
            "state_dict": best_state,
            "config": {
                "embed_dim": d,
                "hidden_dim": args.hidden,
                "out_dim": 1,
                "label_mean": label_mean,
                "label_std": label_std,
                "task": "regression",
            },
        },
        head_path,
    )

    # Reload best state for prediction.
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        all_X = torch.from_numpy(X).float().to(device)
        all_pred_norm = model(all_X).squeeze(1).cpu().numpy()
    all_pred = all_pred_norm * label_std + label_mean

    # predictions.tsv
    pred_path = os.path.join(args.output, "predictions.tsv")
    split_arr = np.full(n, "train", dtype=object)
    split_arr[val_idx] = "val"
    with open(pred_path, "w") as f:
        f.write("name\ttrue\tpredicted\tsplit\n")
        for i in range(n):
            f.write(f"{names[i]}\t{y[i]:.6g}\t{all_pred[i]:.6g}\t{split_arr[i]}\n")

    # metrics.json — overall + val-only.
    def block(mask):
        if mask.sum() < 2:
            return {"n": int(mask.sum()), "mse": float("nan"), "r2": float("nan"),
                    "pearson_r": float("nan"), "spearman_r": float("nan")}
        yt_b = y[mask]
        yp_b = all_pred[mask]
        mse = float(((yt_b - yp_b) ** 2).mean())
        var = float(((yt_b - yt_b.mean()) ** 2).mean()) or 1e-12
        r2 = 1.0 - mse / var
        return {
            "n": int(mask.sum()),
            "mse": mse,
            "r2": r2,
            "pearson_r": pearson(yt_b, yp_b),
            "spearman_r": spearman(yt_b, yp_b),
        }

    val_mask = np.zeros(n, dtype=bool)
    val_mask[val_idx] = True
    train_mask = ~val_mask
    metrics = {
        "task": "regression",
        "embed_dim": d,
        "n_total": n,
        "n_train": int(train_mask.sum()),
        "n_val": int(val_mask.sum()),
        "best_val_mse_normalized": best_val_loss,
        "overall": block(np.ones(n, dtype=bool)),
        "train": block(train_mask),
        "val": block(val_mask),
    }
    metrics_path = os.path.join(args.output, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(
        f"Done. head={head_path} predictions={pred_path} metrics={metrics_path} "
        f"val_pearson={metrics['val']['pearson_r']:.3f}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
