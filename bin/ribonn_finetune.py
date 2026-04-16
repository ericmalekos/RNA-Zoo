#!/usr/bin/env python3
"""
RiboNN transfer learning / fine-tuning wrapper.
Fine-tunes pretrained RiboNN human multi-task model on user-provided TE data
for a specific cell type or condition.

Input: tab-separated file with columns: tx_id, utr5_sequence, cds_sequence,
       utr3_sequence, <target_column> (TE values)
Output: fine-tuned model checkpoint + predictions on held-out test set
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
import pytorch_lightning as pl
import torch
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint

sys.path.insert(0, "/app")
from src.data import RiboNNDataModule
from src.model import RiboNN
from src.utils.helpers import load_config


def unfreeze_batchnorm_layers(model):
    for _name, child in model.named_children():
        if isinstance(child, torch.nn.modules.batchnorm._BatchNorm):
            for param in child.parameters():
                param.requires_grad = True
        unfreeze_batchnorm_layers(child)


def create_transfer_model(config, pretrained_path):
    """Create a transfer learning model from a pretrained multi-task checkpoint."""
    pretrain_config = config.copy()
    pretrain_config["num_targets"] = 78  # pretrained human model has 78 targets
    loaded_model = RiboNN(**pretrain_config)
    loaded_model.load_state_dict(torch.load(pretrained_path, map_location="cpu"))

    # Freeze everything except BatchNorm layers
    loaded_model.freeze()
    unfreeze_batchnorm_layers(loaded_model)

    # Create new model with correct number of targets
    model = RiboNN(**config)

    # Transfer pretrained conv layers
    model.initial_conv = loaded_model.initial_conv
    model.middle_convs = loaded_model.middle_convs
    model.train()

    return model


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune RiboNN on user TE data via transfer learning"
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="Tab-separated training data (tx_id, utr5_sequence, cds_sequence, "
        "utr3_sequence, <target_column>)",
    )
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--target", required=True,
        help="Name of the target column containing TE values",
    )
    parser.add_argument(
        "--phase1-epochs", type=int, default=50,
        help="Epochs for phase 1 (head only, default: 50)",
    )
    parser.add_argument(
        "--phase2-epochs", type=int, default=150,
        help="Epochs for phase 2 (full model, default: 150)",
    )
    parser.add_argument(
        "--patience", type=int, default=50,
        help="Early stopping patience (default: 50)",
    )
    parser.add_argument(
        "--folds", type=int, default=5,
        help="Number of cross-validation folds (default: 5)",
    )
    parser.add_argument(
        "--pretrained-dir",
        default="/app/models/human",
        help="Directory with pretrained model checkpoints and runs.csv",
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Load config
    config = load_config("/app/config/conf.yml")
    config["pad_5_prime"] = True
    config["target_column_pattern"] = args.target
    config["optimizer"] = "AdamW"
    config["lr"] = 0.0001
    config["l2_scale"] = 0.001
    config["with_NAs"] = False
    config["max_shift"] = 0
    config["num_conv_layers"] = 10
    config["symmetric_shift"] = True
    config["remove_extreme_txs"] = False
    config["activation"] = "relu"
    config["max_utr5_len"] = 1_381
    config["max_cds_utr3_len"] = 11_937

    # Load data
    config["tx_info_path"] = args.input
    dm = RiboNNDataModule(config)
    dm.df = dm.df.dropna(subset=[args.target])
    config["num_targets"] = dm.num_targets
    config["len_after_conv"] = dm.get_sequence_length_after_ConvBlocks()

    print(f"Loaded {len(dm.df)} transcripts with target '{args.target}'", file=sys.stderr)

    # Find pretrained checkpoints
    runs_csv = os.path.join(args.pretrained_dir, "runs.csv")
    if not os.path.exists(runs_csv):
        print("Error: runs.csv not found in pretrained dir", file=sys.stderr)
        sys.exit(1)
    pretrain_run_df = pd.read_csv(runs_csv)

    # Assign random folds
    np.random.seed(42)
    dm.df["fold"] = np.random.randint(0, args.folds, size=len(dm.df))

    all_predictions = []

    for test_fold in range(args.folds):
        print(f"\n--- Fold {test_fold}/{args.folds - 1} ---", file=sys.stderr)

        data_test = dm.df.query("fold == @test_fold").reset_index(drop=True)
        data_test["split"] = "test"
        data_train_valid = dm.df.query("fold != @test_fold").reset_index(drop=True)

        # Simple 80/20 train/val split within non-test data
        n_val = max(1, int(len(data_train_valid) * 0.2))
        val_idx = np.random.choice(len(data_train_valid), n_val, replace=False)
        train_idx = np.setdiff1d(range(len(data_train_valid)), val_idx)
        data_train_valid.loc[train_idx, "split"] = "train"
        data_train_valid.loc[val_idx, "split"] = "valid"
        dm.df = pd.concat([data_test, data_train_valid], axis=0, ignore_index=True)

        # Pick a pretrained checkpoint (use first available for this test fold)
        sub_run_df = pretrain_run_df[
            pretrain_run_df["params.test_fold"].astype(int) == test_fold
        ]
        if len(sub_run_df) == 0:
            sub_run_df = pretrain_run_df.head(1)

        pretrained_path = os.path.join(
            args.pretrained_dir,
            str(sub_run_df.iloc[0]["run_id"]),
            "state_dict.pth",
        )
        if not os.path.exists(pretrained_path):
            print(f"  Warning: checkpoint not found at {pretrained_path}, using first available",
                  file=sys.stderr)
            for rid in pretrain_run_df["run_id"]:
                alt = os.path.join(args.pretrained_dir, str(rid), "state_dict.pth")
                if os.path.exists(alt):
                    pretrained_path = alt
                    break

        # Create transfer learning model
        model = create_transfer_model(config, pretrained_path)

        checkpoint = ModelCheckpoint(
            dirpath=os.path.join(args.output, f"fold{test_fold}"),
            save_top_k=1, monitor="val_r2", mode="max",
        )
        early_stopping = EarlyStopping(
            monitor="val_r2", mode="max", patience=args.patience,
        )

        # Phase 1: train head only
        trainer = pl.Trainer(
            max_epochs=args.phase1_epochs,
            gradient_clip_val=0.5,
            enable_progress_bar=True,
            logger=False,
            enable_checkpointing=False,
        )
        trainer.fit(model, datamodule=dm)

        # Phase 2: unfreeze and train full model with lower LR
        model.unfreeze()
        model.lr = 0.00001
        model.optimizers, model.lr_schedulers = model.configure_optimizers()

        trainer = pl.Trainer(
            max_epochs=args.phase2_epochs,
            gradient_clip_val=0.5,
            callbacks=[early_stopping, checkpoint],
            enable_progress_bar=True,
            logger=False,
        )
        trainer.fit(model, datamodule=dm)

        # Reload best and test
        best_ckpt = torch.load(checkpoint.best_model_path, map_location="cpu")
        model.load_state_dict(best_ckpt["state_dict"])
        model.eval()

        test_results = trainer.test(model, datamodule=dm)
        print(f"  Test results: {test_results}", file=sys.stderr)

        # Save predictions for test fold
        preds = trainer.predict(model, datamodule=dm)
        if preds:
            fold_preds = data_test[["tx_id"]].copy()
            fold_preds["fold"] = test_fold
            fold_preds[f"predicted_{args.target}"] = (
                torch.cat([p.squeeze() for p in preds]).numpy()[: len(data_test)]
            )
            all_predictions.append(fold_preds)

    # Save combined predictions
    if all_predictions:
        pred_df = pd.concat(all_predictions, ignore_index=True)
        pred_path = os.path.join(args.output, "predictions.tsv")
        pred_df.to_csv(pred_path, sep="\t", index=False)
        print(f"\nPredictions written to {pred_path}", file=sys.stderr)

    print(f"Done. Fine-tuned models saved to {args.output}/", file=sys.stderr)


if __name__ == "__main__":
    main()
