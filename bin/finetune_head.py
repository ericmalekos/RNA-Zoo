#!/usr/bin/env python3
"""
Generic head trainer for foundation-model linear-probe / MLP / XGBoost fine-tuning.

Inputs: numpy embeddings (N, D) + labels.txt (N rows; numeric for regression,
        any string for classification).
Outputs: best_head.{pt,ubj} + predictions.tsv + metrics.json

Used as Step 3 of the foundation-model fine-tune pipeline:
  TSV → [tsv_to_fasta] → labels (+ optional FASTA) → [predict] → embeddings →
  [this script] → head + predictions

Three head types (--head-type):
  linear  — nn.Linear(D, out_dim)             [default]
  mlp     — Linear(D, 64) → ReLU → Dropout → Linear(64, out_dim)
  xgboost — XGBRegressor / XGBClassifier      [requires xgboost]

Two tasks (--task):
  auto           — detect from labels: numeric (>10 unique) → regression;
                                       int (≤10 unique) or strings → classification
  regression     — force regression (MSE / RMSE)
  classification — force classification (CE / log-loss)

The backbone model is NOT loaded here — the head trains on pre-computed embeddings.
"""

import argparse
import json
import os
import sys

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

# -------------------------- Heads --------------------------

class LinearHead(nn.Module):
    def __init__(self, embed_dim: int, out_dim: int = 1):
        super().__init__()
        self.linear = nn.Linear(embed_dim, out_dim)

    def forward(self, x):
        return self.linear(x)


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


# -------------------------- I/O helpers --------------------------

def parse_fasta_labels(fasta_path):
    if not fasta_path or not os.path.isfile(fasta_path):
        return None
    names = []
    with open(fasta_path) as f:
        for line in f:
            if line.startswith(">"):
                names.append(line[1:].strip())
    return names


def parse_names_file(names_path):
    if not names_path or not os.path.isfile(names_path):
        return None
    with open(names_path) as f:
        return [line.strip() for line in f if line.strip()]


def load_labels_raw(path):
    out = []
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s:
                out.append(s)
    return out


def _is_numeric(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def detect_task(raw_labels, max_classes=10):
    """Heuristic: strings → classification; integer-valued floats with ≤ max_classes
    unique values → classification; otherwise regression."""
    if not all(_is_numeric(s) for s in raw_labels):
        return "classification"
    floats = [float(s) for s in raw_labels]
    unique = set(floats)
    if all(f == int(f) for f in floats) and len(unique) <= max_classes:
        return "classification"
    return "regression"


# -------------------------- Metrics --------------------------

def pearson(y_true, y_pred):
    if y_true.size < 2:
        return float("nan")
    yt = y_true - y_true.mean()
    yp = y_pred - y_pred.mean()
    den = float(np.sqrt((yt * yt).sum() * (yp * yp).sum()))
    if den == 0:
        return float("nan")
    return float((yt * yp).sum() / den)


def spearman(y_true, y_pred):
    if y_true.size < 2:
        return float("nan")
    rt = np.argsort(np.argsort(y_true)).astype(float)
    rp = np.argsort(np.argsort(y_pred)).astype(float)
    return pearson(rt, rp)


def regression_block(y_true, y_pred):
    n = y_true.size
    if n < 2:
        return {"n": int(n), "mse": float("nan"), "r2": float("nan"),
                "pearson_r": float("nan"), "spearman_r": float("nan")}
    mse = float(((y_true - y_pred) ** 2).mean())
    var = float(((y_true - y_true.mean()) ** 2).mean()) or 1e-12
    r2 = 1.0 - mse / var
    return {
        "n": int(n),
        "mse": mse,
        "r2": r2,
        "pearson_r": pearson(y_true, y_pred),
        "spearman_r": spearman(y_true, y_pred),
    }


def classification_block(y_true_int, y_pred_int, probs, class_names):
    """Pure-numpy + optional sklearn for AUROC."""
    n = y_true_int.size
    K = len(class_names)
    if n < 1:
        return {"n": 0, "accuracy": float("nan"), "macro_f1": float("nan"),
                "weighted_f1": float("nan"), "auroc": float("nan"),
                "confusion_matrix": [[0] * K for _ in range(K)], "per_class": {}}

    accuracy = float((y_true_int == y_pred_int).mean())

    cm = np.zeros((K, K), dtype=int)
    for t, p in zip(y_true_int, y_pred_int):  # noqa: B905
        cm[int(t), int(p)] += 1

    per_class = {}
    f1s = []
    weights = []
    for k in range(K):
        tp = int(cm[k, k])
        fp = int(cm[:, k].sum() - tp)
        fn = int(cm[k, :].sum() - tp)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        per_class[class_names[k]] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": int(cm[k, :].sum()),
        }
        f1s.append(f1)
        weights.append(int(cm[k, :].sum()))

    macro_f1 = float(np.mean(f1s))
    total = sum(weights)
    if total > 0:
        weighted_f1 = float(
            sum(f * w for f, w in zip(f1s, weights)) / total  # noqa: B905
        )
    else:
        weighted_f1 = float("nan")

    auroc = float("nan")
    if K == 2 and probs is not None:
        try:
            from sklearn.metrics import roc_auc_score
            if len(set(int(t) for t in y_true_int)) == 2:
                auroc = float(roc_auc_score(y_true_int, probs[:, 1]))
        except ImportError:
            pass
        except ValueError:
            pass

    return {
        "n": int(n),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "auroc": auroc,
        "confusion_matrix": cm.tolist(),
        "per_class": per_class,
    }


# -------------------------- Training paths --------------------------

def train_torch_head(X, y, val_idx, train_idx, args, head_type, task, num_classes):
    """Shared train loop for linear/mlp.
       y is normalized float (regression) or int class indices (classification).
       Returns (model, best_state, best_val_loss)."""
    n, d = X.shape
    device = "cuda" if torch.cuda.is_available() else "cpu"

    out_dim = num_classes if task == "classification" else 1
    if head_type == "linear":
        model = LinearHead(d, out_dim).to(device)
    else:
        model = MLPHead(d, hidden_dim=args.hidden, out_dim=out_dim).to(device)

    print(
        f"head trainer: head_type={head_type}, task={task}, device={device}, "
        f"embed_dim={d}, n_train={len(train_idx)}, n_val={len(val_idx)}, out_dim={out_dim}",
        file=sys.stderr,
    )

    Xt = torch.from_numpy(X[train_idx]).float().to(device)
    Xv = torch.from_numpy(X[val_idx]).float().to(device)

    if task == "regression":
        yt = torch.from_numpy(y[train_idx]).float().unsqueeze(1).to(device)
        yv = torch.from_numpy(y[val_idx]).float().unsqueeze(1).to(device)
        loss_fn = nn.MSELoss()
    else:
        yt = torch.from_numpy(y[train_idx]).long().to(device)
        yv = torch.from_numpy(y[val_idx]).long().to(device)
        loss_fn = nn.CrossEntropyLoss()

    opt = optim.Adam(model.parameters(), lr=args.lr)

    best_val_loss = float("inf")
    best_state = None
    epochs_no_improve = 0
    bs = args.batch_size

    for epoch in range(args.epochs):
        model.train()
        perm = torch.randperm(Xt.shape[0], device=device)
        total_loss = 0.0
        for s in range(0, Xt.shape[0], bs):
            sel = perm[s:s + bs]
            opt.zero_grad()
            pred = model(Xt[sel])
            loss = loss_fn(pred, yt[sel])
            loss.backward()
            opt.step()
            total_loss += float(loss.detach()) * sel.shape[0]
        train_loss = total_loss / Xt.shape[0]

        model.eval()
        with torch.no_grad():
            pv = model(Xv)
            val_loss = float(loss_fn(pv, yv))

        if val_loss < best_val_loss - 1e-6:
            best_val_loss = val_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        print(
            f"epoch {epoch + 1}/{args.epochs}: train_loss={train_loss:.4f} "
            f"val_loss={val_loss:.4f} best={best_val_loss:.4f} "
            f"no_improve={epochs_no_improve}",
            file=sys.stderr,
        )
        if epochs_no_improve >= args.patience:
            print(f"early-stop at epoch {epoch + 1}", file=sys.stderr)
            break

    if best_state is None:
        best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    return model, best_state, best_val_loss


def predict_torch_head(model, best_state, X, task, label_mean, label_std):
    """Returns (preds, probs). For regression: preds float (n,), probs None.
       For classification: preds int (n,), probs (n, K)."""
    model.load_state_dict(best_state)
    model.eval()
    device = next(model.parameters()).device
    with torch.no_grad():
        all_X = torch.from_numpy(X).float().to(device)
        out = model(all_X).cpu().numpy()
    if task == "regression":
        preds = out.squeeze(-1) * label_std + label_mean
        return preds, None
    out_t = torch.from_numpy(out)
    probs = torch.softmax(out_t, dim=-1).numpy()
    pred_int = probs.argmax(axis=-1)
    return pred_int, probs


def train_xgboost_head(X, y, val_idx, train_idx, args, task, num_classes):
    """XGBoost regressor or classifier with early stopping on the val split."""
    import xgboost as xgb

    common = dict(
        n_estimators=200,
        max_depth=6,
        learning_rate=args.lr,
        random_state=args.seed,
        early_stopping_rounds=max(2, args.patience * 2),
    )
    if task == "regression":
        common["eval_metric"] = "rmse"
        model = xgb.XGBRegressor(**common)
    else:
        if num_classes == 2:
            common["objective"] = "binary:logistic"
            common["eval_metric"] = "logloss"
        else:
            common["objective"] = "multi:softprob"
            common["eval_metric"] = "mlogloss"
            common["num_class"] = num_classes
        model = xgb.XGBClassifier(**common)

    model.fit(
        X[train_idx], y[train_idx],
        eval_set=[(X[val_idx], y[val_idx])],
        verbose=False,
    )
    best_iter = getattr(model, "best_iteration", None)
    print(
        f"xgboost {task}: best_iteration={best_iter}",
        file=sys.stderr,
    )
    return model


def predict_xgboost_head(model, X, task):
    if task == "regression":
        return model.predict(X), None
    probs = model.predict_proba(X)
    pred_int = probs.argmax(axis=-1)
    return pred_int, probs


# -------------------------- Main --------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-e", "--embeddings", required=True, help="Path to .npy (N, D)")
    parser.add_argument("-l", "--labels", required=True, help="Path to labels.txt (N rows)")
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    names_group = parser.add_mutually_exclusive_group()
    names_group.add_argument(
        "--names-fasta", default=None,
        help="Optional FASTA whose headers provide row names for predictions.tsv.",
    )
    names_group.add_argument(
        "--names", dest="names", default=None,
        help="Optional plain-text file (one name per line, same order as labels).",
    )
    parser.add_argument(
        "--head-type", choices=["linear", "mlp", "xgboost"], default="linear",
        help="Head architecture (default: linear). 'xgboost' requires the "
             "rnazoo-finetune-head image.",
    )
    parser.add_argument(
        "--task", choices=["auto", "regression", "classification"], default="auto",
        help="Task type. 'auto' (default) detects from labels.",
    )
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--hidden", type=int, default=64,
                        help="Hidden-dim for --head-type mlp (ignored otherwise)")
    parser.add_argument("--val-frac", type=float, default=0.2)
    parser.add_argument("--patience", type=int, default=5,
                        help="Early-stopping patience (epochs without val improvement)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # Embeddings
    X = np.load(args.embeddings)
    if X.ndim != 2:
        print(f"ERROR: embeddings must be 2D (N,D); got shape {X.shape}", file=sys.stderr)
        sys.exit(1)
    n, d = X.shape

    # Labels (raw)
    raw_labels = load_labels_raw(args.labels)
    if len(raw_labels) != n:
        print(
            f"ERROR: labels rows ({len(raw_labels)}) != embeddings rows ({n})",
            file=sys.stderr,
        )
        sys.exit(1)

    # Task
    task = detect_task(raw_labels) if args.task == "auto" else args.task

    # Encode labels for the chosen task
    label_mean = label_std = None
    class_names = None
    num_classes = None
    if task == "regression":
        try:
            y_orig = np.array([float(s) for s in raw_labels], dtype=np.float32)
        except ValueError as exc:
            print(
                f"ERROR: regression task requires numeric labels: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)
        y_orig_display = y_orig
    else:
        # Stable order: numeric ascending, then strings alphabetical
        unique = sorted(set(raw_labels), key=lambda s: (
            (0, float(s)) if _is_numeric(s) else (1, s)
        ))
        class_names = unique
        if len(class_names) < 2:
            print(
                f"ERROR: classification needs ≥ 2 distinct classes; got {len(class_names)}",
                file=sys.stderr,
            )
            sys.exit(1)
        label_to_int = {lab: i for i, lab in enumerate(class_names)}
        y_orig = np.array([label_to_int[s] for s in raw_labels], dtype=np.int64)
        y_orig_display = np.array(raw_labels, dtype=object)
        num_classes = len(class_names)

    # Names
    names = parse_fasta_labels(args.names_fasta) or parse_names_file(args.names)
    if names is None or len(names) != n:
        names = [f"row_{i}" for i in range(n)]

    # Train/val split (deterministic)
    rng = np.random.RandomState(args.seed)
    idx = rng.permutation(n)
    n_val = max(1, int(round(n * args.val_frac)))
    val_idx = idx[:n_val]
    train_idx = idx[n_val:]
    if train_idx.size < 1:
        train_idx = idx
        val_idx = idx[:1]

    os.makedirs(args.output, exist_ok=True)
    best_val_loss = float("nan")

    # ----- Train + predict -----

    if args.head_type in ("linear", "mlp"):
        if task == "regression":
            label_mean = float(y_orig[train_idx].mean())
            label_std = float(y_orig[train_idx].std()) or 1.0
            y_for_train = (y_orig - label_mean) / label_std
        else:
            y_for_train = y_orig

        model, best_state, best_val_loss = train_torch_head(
            X, y_for_train, val_idx, train_idx, args, args.head_type, task, num_classes,
        )
        all_pred, all_probs = predict_torch_head(
            model, best_state, X, task, label_mean or 0.0, label_std or 1.0,
        )

        head_path = os.path.join(args.output, "best_head.pt")
        torch.save({
            "state_dict": best_state,
            "config": {
                "head_type": args.head_type,
                "task": task,
                "embed_dim": d,
                "hidden_dim": args.hidden if args.head_type == "mlp" else None,
                "out_dim": num_classes if task == "classification" else 1,
                "label_mean": label_mean,
                "label_std": label_std,
                "class_names": class_names,
            },
        }, head_path)

    else:  # xgboost
        try:
            import xgboost  # noqa: F401
        except ImportError:
            print(
                "ERROR: xgboost is not installed in this environment. Use the "
                "rnazoo-finetune-head image (FINETUNE_HEAD_ONLY path).",
                file=sys.stderr,
            )
            sys.exit(2)

        model = train_xgboost_head(X, y_orig, val_idx, train_idx, args, task, num_classes or 0)
        all_pred, all_probs = predict_xgboost_head(model, X, task)

        head_path = os.path.join(args.output, "best_head.ubj")
        model.save_model(head_path)
        config_path = os.path.join(args.output, "best_head_config.json")
        with open(config_path, "w") as f:
            json.dump({
                "head_type": "xgboost",
                "task": task,
                "embed_dim": d,
                "out_dim": num_classes if task == "classification" else 1,
                "class_names": class_names,
            }, f, indent=2)

    # ----- predictions.tsv -----

    pred_path = os.path.join(args.output, "predictions.tsv")
    split_arr = np.full(n, "train", dtype=object)
    split_arr[val_idx] = "val"

    with open(pred_path, "w") as f:
        if task == "regression":
            f.write("name\ttrue\tpredicted\tsplit\n")
            for i in range(n):
                f.write(f"{names[i]}\t{y_orig[i]:.6g}\t{all_pred[i]:.6g}\t{split_arr[i]}\n")
        else:
            cols = ["name", "true", "predicted"]
            if all_probs is not None:
                cols += [f"prob_{c}" for c in class_names]
            cols.append("split")
            f.write("\t".join(cols) + "\n")
            for i in range(n):
                row = [
                    names[i],
                    str(y_orig_display[i]),
                    class_names[int(all_pred[i])],
                ]
                if all_probs is not None:
                    row += [f"{all_probs[i, k]:.6g}" for k in range(num_classes)]
                row.append(split_arr[i])
                f.write("\t".join(row) + "\n")

    # ----- metrics.json -----

    val_mask = np.zeros(n, dtype=bool)
    val_mask[val_idx] = True
    train_mask = ~val_mask

    common = {
        "task": task,
        "head_type": args.head_type,
        "embed_dim": d,
        "n_total": n,
        "n_train": int(train_mask.sum()),
        "n_val": int(val_mask.sum()),
        "best_val_loss": best_val_loss,
    }
    if task == "regression":
        metrics = {
            **common,
            "overall": regression_block(y_orig, all_pred),
            "train": regression_block(y_orig[train_mask], all_pred[train_mask]),
            "val": regression_block(y_orig[val_mask], all_pred[val_mask]),
        }
        summary = f"val_pearson={metrics['val']['pearson_r']:.3f}"
    else:
        metrics = {
            **common,
            "num_classes": num_classes,
            "class_names": class_names,
            "overall": classification_block(y_orig, all_pred, all_probs, class_names),
            "train": classification_block(
                y_orig[train_mask], all_pred[train_mask],
                all_probs[train_mask] if all_probs is not None else None,
                class_names,
            ),
            "val": classification_block(
                y_orig[val_mask], all_pred[val_mask],
                all_probs[val_mask] if all_probs is not None else None,
                class_names,
            ),
        }
        summary = (
            f"val_acc={metrics['val']['accuracy']:.3f} "
            f"val_macro_f1={metrics['val']['macro_f1']:.3f}"
        )

    metrics_path = os.path.join(args.output, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(
        f"Done. head={head_path} predictions={pred_path} metrics={metrics_path} {summary}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
