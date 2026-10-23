#!/usr/bin/env python3
"""
CLI wrapper for Saluki mRNA half-life prediction (Agarwal & Kelley, Genome Biology 2022).

Saluki reads six channels per nucleotide: A, C, G, T, a codon-frame bit and a
splice-junction bit. As in upstream's own scorer (basenji bin/saluki_ssd.py,
rna_1hot_splice), the frame bit is set at the first nucleotide of each codon inside the
CDS, and the splice bit at the last nucleotide of every exon, in transcript order.

Input FASTA convention (unchanged from earlier RNA-Zoo releases): 5' and 3' UTRs in
lowercase, the CDS in uppercase. Upstream's saluki_predict_fasta.py, which earlier releases
ran, never sets the splice channel; this wrapper sets it from --exons when given:

    --exons TSV   columns: name, exon_lengths (comma-separated, in transcript order, summing
                  to the sequence length; names match the FASTA headers' first word)

Transcripts without exon lengths are predicted with the splice channel at zero, as before,
and listed in a warning: those predictions differ from what the model saw in training.

Output: preds.npy (N x 1 x 50 ensemble members, as before), names.txt, and
predictions.tsv (name, mean over the 50 members, standard deviation, splice_channel_set).
The value is Saluki's unitless consensus half-life score (the first principal component of
standardized log half-lives across studies), not a half-life in hours or log2 units.
"""

import argparse
import glob
import json
import os
import sys

import numpy as np

NUC = {"A": 0, "C": 1, "G": 2, "T": 3, "U": 3}


def parse_fasta(path):
    name, parts = None, []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(parts)
                name, parts = line[1:].split()[0], []
            elif line:
                parts.append(line)
    if name is not None:
        yield name, "".join(parts)


def cds_from_case(seq):
    """1-based inclusive CDS bounds from the uppercase run; None when there is none."""
    upper = [i for i, c in enumerate(seq) if c.isupper()]
    if not upper:
        return None
    return upper[0] + 1, upper[-1] + 1


def encode(seq, cds, exon_lengths, seq_len):
    """(seq_len, 6) bool: zeros appended when short, the last seq_len positions kept when long,
    exactly as upstream's FASTA script pads and truncates."""
    L = len(seq)
    x = np.zeros((L, 6), dtype=bool)
    for i, nt in enumerate(seq.upper()):
        k = NUC.get(nt)
        if k is not None:
            x[i, k] = True
    if cds is not None:
        s0, e0 = cds[0] - 1, cds[1]
        if (e0 - s0) % 3 == 0:                 # same validity rule as rna_1hot_splice
            x[s0:e0:3, 4] = True
    if exon_lengths is not None:
        if sum(exon_lengths) != L:
            raise ValueError(f"exon lengths sum to {sum(exon_lengths)}, sequence has {L} nt")
        x[np.cumsum(exon_lengths) - 1, 5] = True
    if L < seq_len:
        x = np.concatenate([x, np.zeros((seq_len - L, 6), dtype=bool)], axis=0)
    elif L > seq_len:
        x = x[-seq_len:]
    return x


def read_exons(path):
    exons = {}
    with open(path) as fh:
        header = fh.readline().rstrip("\n").split("\t")
        if header[:2] != ["name", "exon_lengths"]:
            raise SystemExit(f"--exons: expected columns 'name' and 'exon_lengths', got {header}")
        for line in fh:
            if not line.strip():
                continue
            name, lengths = line.rstrip("\n").split("\t")[:2]
            exons[name] = [int(v) for v in lengths.split(",") if v]
    return exons


def main():
    ap = argparse.ArgumentParser(description="Predict mRNA half-life score with Saluki")
    ap.add_argument("-i", "--input", required=True,
                    help="FASTA, UTRs lowercase and CDS uppercase")
    ap.add_argument("-o", "--output", required=True, help="Output directory")
    ap.add_argument("--exons", default=None,
                    help="TSV of exon lengths per transcript (name, exon_lengths)")
    ap.add_argument("--data-head", type=int, default=0, help="0 human (default), 1 mouse")
    ap.add_argument("--models", default="/opt/saluki_models",
                    help="Directory of the 50-member ensemble (default: the image's copy)")
    a = ap.parse_args()
    os.makedirs(a.output, exist_ok=True)

    sys.path.insert(0, "/opt/basenji")
    from basenji import rnann

    params = json.load(open(os.path.join(a.models, "params.json")))
    seq_len = params["model"]["seq_length"]
    exons = read_exons(a.exons) if a.exons else {}

    names, rows, spliced, missing = [], [], [], []
    for name, seq in parse_fasta(a.input):
        el = exons.get(name)
        if el is None:
            missing.append(name)
        names.append(name)
        spliced.append(el is not None)
        rows.append(encode(seq, cds_from_case(seq), el, seq_len))
    if not rows:
        raise SystemExit("no sequences in the input")
    if missing:
        print(f"WARNING: no exon lengths for {len(missing)} of {len(names)} transcripts; their "
              "splice-junction channel is left at zero, which differs from Saluki's training "
              "input. Give --exons (name, exon_lengths) to set it. First few: "
              + ", ".join(missing[:5]), file=sys.stderr)
    X = np.stack(rows).astype("float32")

    model_str = f"model{a.data_head}_best.h5"
    folds = len(glob.glob(f"{a.models}/f*_c0/train/{model_str}"))
    crosses = len(glob.glob(f"{a.models}/f0_c*/train/{model_str}"))
    if folds * crosses == 0:
        raise SystemExit(f"no ensemble members named {model_str} under {a.models}")
    model = rnann.RnaNN(params["model"])
    preds = []
    for fi in range(folds):
        for ci in range(crosses):
            model.restore(f"{a.models}/f{fi}_c{ci}/train/{model_str}", a.data_head)
            model.build_ensemble("0")
            preds.append(model.predict(X))
    P = np.transpose(np.array(preds), [1, 2, 0])      # (N, 1, members)
    np.save(os.path.join(a.output, "preds.npy"), P)
    with open(os.path.join(a.output, "names.txt"), "w") as fh:
        fh.write("\n".join(names) + "\n")
    mean, sd = P.mean(axis=-1).ravel(), P.std(axis=-1).ravel()
    with open(os.path.join(a.output, "predictions.tsv"), "w") as fh:
        fh.write("name\tsaluki_score_mean\tsaluki_score_sd\tsplice_channel_set\n")
        for n, m, s, sp in zip(names, mean, sd, spliced):  # noqa: B905 (image runs Python 3.8)
            fh.write(f"{n}\t{m:.6f}\t{s:.6f}\t{str(sp).lower()}\n")
    print(f"Predicted {len(names)} transcripts with {folds * crosses} ensemble members",
          file=sys.stderr)


if __name__ == "__main__":
    main()
