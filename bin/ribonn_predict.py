#!/usr/bin/env python3
"""
RiboNN prediction wrapper.
Supports both bundled pretrained models (multi-task, 78 cell types) and
user-provided fine-tuned checkpoints (single target).

When --checkpoint is provided, loads the fine-tuned model and predicts
for the single target it was trained on.
When --checkpoint is omitted, falls back to the upstream prediction flow
using pretrained nested cross-validation models.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, "/app")
from src.data import RiboNNDataModule
from src.model import RiboNN
from src.utils.helpers import load_config


def predict_with_finetuned(input_path, checkpoint_path, output_path, target_name):
    """Run prediction using a fine-tuned single-target checkpoint."""

    config = load_config("/app/config/conf.yml")
    config["pad_5_prime"] = True
    config["target_column_pattern"] = None
    config["num_targets"] = 1
    config["max_utr5_len"] = 1_381
    config["max_cds_utr3_len"] = 11_937
    config["remove_extreme_txs"] = False
    config["tx_info_path"] = input_path
    config["num_conv_layers"] = 10
    config["activation"] = "relu"
    config["with_NAs"] = False
    config["max_shift"] = 0
    config["symmetric_shift"] = True

    dm = RiboNNDataModule(config)
    config["len_after_conv"] = dm.get_sequence_length_after_ConvBlocks()

    model = RiboNN(**config)

    # Fine-tuned checkpoints are PyTorch Lightning .ckpt files
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    if "state_dict" in ckpt:
        model.load_state_dict(ckpt["state_dict"])
    else:
        model.load_state_dict(ckpt)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    predictions = []
    with torch.no_grad():
        for batch in dm.predict_dataloader():
            preds = model(batch.to(device))
            predictions.append(preds.cpu().numpy())

    preds = np.concatenate(predictions, axis=0).squeeze()

    col_name = f"predicted_{target_name}" if target_name else "predicted_TE"
    df = dm.df[["tx_id"]].copy()
    df[col_name] = preds

    os.makedirs(output_path, exist_ok=True)
    out_file = os.path.join(output_path, "prediction_output.txt")
    df.to_csv(out_file, sep="\t", index=False)
    print(f"Predictions written to {out_file}", file=sys.stderr)


def predict_with_pretrained(input_path, species, output_path):
    """Run prediction using bundled pretrained models (upstream flow)."""
    from src.predict import predict_using_nested_cross_validation_models

    run_df = pd.read_csv(f"models/{species}/runs.csv")
    result_df = predict_using_nested_cross_validation_models(
        input_path=input_path,
        species=species,
        run_df=run_df,
    )

    os.makedirs(output_path, exist_ok=True)
    out_file = os.path.join(output_path, "prediction_output.txt")
    result_df.to_csv(out_file, sep="\t", index=False)
    print(f"Predictions written to {out_file}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Predict translation efficiency with RiboNN"
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="Tab-separated input (tx_id, utr5_sequence, cds_sequence, utr3_sequence)",
    )
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--species", default="human", choices=["human", "mouse"],
        help="Species for pretrained models (default: human). Ignored when --checkpoint is set.",
    )
    parser.add_argument(
        "--checkpoint", default=None,
        help="Path to a fine-tuned checkpoint (.ckpt) to use instead of bundled pretrained models",
    )
    parser.add_argument(
        "--target", default=None,
        help="Name of the target column the fine-tuned model was trained on "
        "(used for output column naming, default: TE)",
    )
    args = parser.parse_args()

    if args.checkpoint:
        print(f"Using fine-tuned checkpoint: {args.checkpoint}", file=sys.stderr)
        predict_with_finetuned(args.input, args.checkpoint, args.output, args.target)
    else:
        predict_with_pretrained(args.input, args.species, args.output)


if __name__ == "__main__":
    main()
