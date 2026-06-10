#!/usr/bin/env python3
"""
CLI wrapper for Orthrus mature-mRNA embedding extraction.

4-track variants (sequence-only, FASTA input only):
  4track       antichronology/orthrus-4-track       512-d  [default]
  base-4track  quietflamingo/orthrus-base-4-track   256-d
  large-4track quietflamingo/orthrus-large-4-track  512-d

6-track variants (FASTA + CDS/splice annotation required):
  6track       antichronology/orthrus-6-track        512-d  contrastive
  small-6track antichronology/orthrus-small-6-track  256-d  contrastive
  mlm-6track   antichronology/orthrus-mlm-6-track    512-d  contrastive + MLM
  large-6track quietflamingo/orthrus-large-6-track   512-d  contrastive

Annotation input (required for 6-track variants):
  --annotation TSV  Tab-separated: name, cds_start, cds_end[, exon_lengths]
                    name        matches FASTA header (before first space)
                    cds_start   0-based transcript-relative CDS start
                    cds_end     0-based exclusive CDS end
                    exon_lengths  optional: comma-sep exon lengths for splice track
  --gtf FILE        GENCODE/Ensembl GTF; auto-derives annotation for each
                    transcript found in the FASTA. Transcript IDs are matched
                    by stripping any version suffix (e.g. ENST00000123.4 → ENST00000123).
"""

import argparse
import gzip
import os
import sys
from collections import defaultdict

import numpy as np
import torch
from transformers import AutoModel

WEIGHTS_ROOT = "/opt/orthrus_weights"
DEFAULT_VARIANT = "4track"

VARIANTS = {
    # 4-track: sequence-only
    "4track": {
        "local_dir": "orthrus-4-track",
        "embed_dim": 512,
        "n_tracks": 4,
    },
    "base-4track": {
        "local_dir": "orthrus-base-4-track",
        "embed_dim": 256,
        "n_tracks": 4,
    },
    "large-4track": {
        "local_dir": "orthrus-large-4-track",
        "embed_dim": 512,
        "n_tracks": 4,
    },
    # 6-track: sequence + CDS + splice annotation
    "6track": {
        "local_dir": "orthrus-6-track",
        "embed_dim": 512,
        "n_tracks": 6,
    },
    "small-6track": {
        "local_dir": "orthrus-small-6-track",
        "embed_dim": 256,
        "n_tracks": 6,
    },
    "mlm-6track": {
        "local_dir": "orthrus-mlm-6-track",
        "embed_dim": 512,
        "n_tracks": 6,
    },
    "large-6track": {
        "local_dir": "orthrus-large-6-track",
        "embed_dim": 512,
        "n_tracks": 6,
    },
    # Legacy alias kept for backward compatibility
    "v1_4_track": {
        "local_dir": "orthrus-4-track",
        "embed_dim": 512,
        "n_tracks": 4,
    },
}


# ---------------------------------------------------------------------------
# FASTA / annotation parsing
# ---------------------------------------------------------------------------

def parse_fasta(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as f:
        header, parts = None, []
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(parts)
                header = line[1:]
                parts = []
            elif line:
                parts.append(line)
        if header is not None:
            yield header, "".join(parts)


def parse_annotation_tsv(path):
    """
    Returns dict: short_name -> {'cds_start': int, 'cds_end': int, 'exon_lengths': list|None}
    Accepts tab- or comma-delimited files with a header row.
    Required columns: name, cds_start, cds_end
    Optional column: exon_lengths (comma-sep ints)
    """
    annotation = {}
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as f:
        header = None
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            delim = "\t" if "\t" in line else ","
            fields = line.split(delim)
            if header is None:
                header = [h.strip().lower() for h in fields]
                continue
            row = dict(zip(header, [v.strip() for v in fields], strict=False))
            name = row.get("name") or row.get("transcript_id") or row.get("id") or ""
            if not name:
                continue
            short = name.split()[0].split("|")[0]
            try:
                cds_start = int(row["cds_start"])
                cds_end = int(row["cds_end"])
            except (KeyError, ValueError):
                print(f"Warning: bad cds_start/cds_end for {name}, skipping", file=sys.stderr)
                continue
            exon_raw = row.get("exon_lengths", "").strip()
            exon_lengths = (
                [int(x) for x in exon_raw.split(",") if x.strip()]
                if exon_raw else None
            )
            annotation[short] = {
                "cds_start": cds_start,
                "cds_end": cds_end,
                "exon_lengths": exon_lengths,
            }
    return annotation


def _parse_gtf_attrs(attr_str):
    attrs = {}
    for part in attr_str.strip().rstrip(";").split(";"):
        part = part.strip()
        if not part:
            continue
        try:
            key, _, val = part.partition(" ")
            attrs[key.strip()] = val.strip().strip('"')
        except ValueError:
            pass
    return attrs


def parse_gtf(path, wanted_ids=None):
    """
    Parse GENCODE/Ensembl GTF → per-transcript annotation dict.
    Returns dict: transcript_id -> {'cds_start': int, 'cds_end': int, 'exon_lengths': list}
    All coordinates are 0-based, transcript-relative.
    wanted_ids: set of bare transcript IDs (no version) to filter; None = all.
    """
    exons_by_tx = defaultdict(list)   # tid -> [(chrom, start, end, strand), ...]
    cds_by_tx = defaultdict(list)     # tid -> [(chrom, start, end), ...]

    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as f:
        for line in f:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 9:
                continue
            feature = fields[2]
            if feature not in ("exon", "CDS"):
                continue
            chrom = fields[0]
            start = int(fields[3]) - 1   # GTF is 1-based inclusive → 0-based
            end = int(fields[4])          # 0-based exclusive
            strand = fields[6]
            attrs = _parse_gtf_attrs(fields[8])
            tid = attrs.get("transcript_id", "")
            # strip version suffix for matching
            bare = tid.split(".")[0]
            if wanted_ids is not None and bare not in wanted_ids:
                continue
            if feature == "exon":
                exons_by_tx[tid].append((chrom, start, end, strand))
            else:
                cds_by_tx[tid].append((chrom, start, end))

    result = {}
    for tid, exon_list in exons_by_tx.items():
        strand = exon_list[0][3]
        # sort exons in transcript order
        if strand == "-":
            exon_list.sort(key=lambda x: -x[2])
        else:
            exon_list.sort(key=lambda x: x[1])

        exon_lengths = [e[2] - e[1] for e in exon_list]

        # build cumulative start positions of each exon in transcript space
        cum = [0]
        for el in exon_lengths:
            cum.append(cum[-1] + el)

        # convert genomic CDS coords → transcript-relative
        cds_start_tx, cds_end_tx = None, None
        if cds_by_tx.get(tid):
            cds_gen_start = min(c[1] for c in cds_by_tx[tid])
            cds_gen_end = max(c[2] for c in cds_by_tx[tid])

            # find which exon the CDS start/end falls in
            def genomic_to_tx(gpos, exon_list, strand, cum):
                if strand == "-":
                    for i, (_, es, ee, _) in enumerate(exon_list):
                        if es <= gpos < ee:
                            return cum[i] + (ee - 1 - gpos)
                else:
                    for i, (_, es, ee, _) in enumerate(exon_list):
                        if es <= gpos < ee:
                            return cum[i] + (gpos - es)
                return None

            if strand == "-":
                s = genomic_to_tx(cds_gen_end - 1, exon_list, strand, cum)
                e = genomic_to_tx(cds_gen_start, exon_list, strand, cum)
                if s is not None and e is not None:
                    cds_start_tx, cds_end_tx = s, e + 1
            else:
                s = genomic_to_tx(cds_gen_start, exon_list, strand, cum)
                e = genomic_to_tx(cds_gen_end - 1, exon_list, strand, cum)
                if s is not None and e is not None:
                    cds_start_tx, cds_end_tx = s, e + 1

        bare = tid.split(".")[0]
        result[bare] = {
            "cds_start": cds_start_tx if cds_start_tx is not None else 0,
            "cds_end": cds_end_tx if cds_end_tx is not None else sum(exon_lengths),
            "exon_lengths": exon_lengths,
        }

    return result


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------

def build_6track(seq_oh4, cds_start, cds_end, exon_lengths=None):
    """
    Build (L, 6) array from (L, 4) one-hot + annotation.
    Track 5: 1 at first nt of each codon within CDS.
    Track 6: 1 at last nt of each internal exon junction (splice site).
    """
    L = seq_oh4.shape[0]
    cds_track = np.zeros(L, dtype=np.float32)
    for pos in range(max(0, cds_start), min(L, cds_end), 3):
        cds_track[pos] = 1.0

    splice_track = np.zeros(L, dtype=np.float32)
    if exon_lengths and len(exon_lengths) > 1:
        pos = 0
        for el in exon_lengths[:-1]:
            pos += el
            if 0 < pos < L:
                splice_track[pos - 1] = 1.0  # last nt of exon

    return np.concatenate(
        [seq_oh4, cds_track[:, None], splice_track[:, None]], axis=1
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract Orthrus embeddings from mature mRNA sequences"
    )
    parser.add_argument("-i", "--input", required=True,
                        help="FASTA of mature mRNA sequences (may be .gz)")
    parser.add_argument("-o", "--output", required=True,
                        help="Output directory for embedding files")
    parser.add_argument(
        "--variant", default=DEFAULT_VARIANT, choices=sorted(VARIANTS.keys()),
        help=f"Model variant (default: {DEFAULT_VARIANT}). "
             "4-track variants require no annotation. "
             "6-track variants require --annotation or --gtf.",
    )
    parser.add_argument(
        "--annotation", metavar="TSV",
        help="Tab-separated annotation file: name, cds_start, cds_end[, exon_lengths]. "
             "Required for 6-track variants.",
    )
    parser.add_argument(
        "--gtf", metavar="GTF",
        help="GENCODE/Ensembl GTF (.gtf or .gtf.gz) to auto-derive CDS and "
             "splice-site annotation. Transcript IDs matched by stripping "
             "version suffix. Overridden by --annotation if both supplied.",
    )
    parser.add_argument("--per-token", action="store_true",
                        help="Also save per-token embeddings (L×D .npy per sequence)")
    parser.add_argument("--min-len", type=int, default=200,
                        help="Warn when sequence is shorter than this (default: 200)")
    args = parser.parse_args()

    n_tracks = VARIANTS[args.variant]["n_tracks"]
    is_6track = n_tracks == 6

    # Validate annotation inputs
    if is_6track and not args.annotation and not args.gtf:
        print(
            f"Error: variant '{args.variant}' is a 6-track model. "
            "Provide --annotation TSV or --gtf GTF.",
            file=sys.stderr,
        )
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}", file=sys.stderr)
    if device.type != "cuda":
        print(
            "Warning: Orthrus uses Mamba's CUDA selective-scan kernel; "
            "running on CPU is not supported by the bundled mamba-ssm wheel.",
            file=sys.stderr,
        )

    # Load model
    variant_cfg = VARIANTS[args.variant]
    weights_path = os.path.join(WEIGHTS_ROOT, variant_cfg["local_dir"])
    print(
        f"Loading Orthrus variant '{args.variant}' "
        f"({n_tracks}-track, {variant_cfg['embed_dim']}-d) from {weights_path}",
        file=sys.stderr,
    )
    model = AutoModel.from_pretrained(
        weights_path, trust_remote_code=True,
    ).to(device).eval()

    # Parse sequences first so we can filter GTF by transcript ID
    sequences = []
    short_count = 0
    for header, seq in parse_fasta(args.input):
        seq = seq.upper().replace("U", "T")
        if not seq:
            print(f"Warning: {header} is empty, skipping", file=sys.stderr)
            continue
        if len(seq) < args.min_len:
            short_count += 1
            print(
                f"Warning: {header} is {len(seq)} nt (<{args.min_len}); "
                "may be out-of-distribution",
                file=sys.stderr,
            )
        # short ID for annotation lookup: first token, first pipe segment, strip version
        short = header.split()[0].split("|")[0].split(".")[0]
        sequences.append((header, short, seq))

    if not sequences:
        print("Error: no valid sequences found in input", file=sys.stderr)
        sys.exit(1)

    # Load annotation
    annotation = {}
    if is_6track:
        if args.annotation:
            annotation = parse_annotation_tsv(args.annotation)
            print(f"Loaded annotation for {len(annotation)} transcripts from TSV", file=sys.stderr)
        elif args.gtf:
            wanted = {short for _, short, _ in sequences}
            print(f"Parsing GTF for {len(wanted)} transcript IDs...", file=sys.stderr)
            annotation = parse_gtf(args.gtf, wanted_ids=wanted)
            print(f"Found annotation for {len(annotation)} transcripts in GTF", file=sys.stderr)

    os.makedirs(args.output, exist_ok=True)

    print(f"Processing {len(sequences)} sequences...", file=sys.stderr)

    all_embs = []
    all_labels = []
    missing_annotation = []

    for header, short, seq in sequences:
        L = len(seq)

        if is_6track:
            ann = annotation.get(short)
            if ann is None:
                # try full header as fallback
                ann = annotation.get(header.split()[0])
            if ann is None:
                print(
                    f"Warning: no annotation for '{short}' — skipping",
                    file=sys.stderr,
                )
                missing_annotation.append(short)
                continue

            # Build 4-track one-hot then extend to 6-track
            oh4 = model.seq_to_oh(seq).cpu().numpy()  # (L, 4)
            x = build_6track(oh4, ann["cds_start"], ann["cds_end"], ann["exon_lengths"])
            x_t = torch.tensor(x, dtype=torch.float32).unsqueeze(0).to(device)  # (1, L, 6)
        else:
            x_t = model.seq_to_oh(seq).unsqueeze(0).to(device)  # (1, L, 4)

        lengths = torch.tensor([L], device=device)

        with torch.no_grad():
            emb = model.representation(x_t, lengths, channel_last=True)  # (1, D)
        all_embs.append(emb.squeeze(0).cpu().numpy())
        all_labels.append(header)

        if args.per_token:
            with torch.no_grad():
                tokens = model.representation_unpooled(x_t, channel_last=True)  # (1, L, D)
            safe = header.replace("/", "_").replace(" ", "_")
            np.save(
                os.path.join(args.output, f"{safe}_tokens.npy"),
                tokens.squeeze(0).cpu().numpy(),
            )

    if not all_embs:
        print("Error: no sequences were successfully embedded", file=sys.stderr)
        sys.exit(1)

    embs = np.stack(all_embs)
    np.save(os.path.join(args.output, "sequence_embeddings.npy"), embs)
    with open(os.path.join(args.output, "labels.txt"), "w") as f:
        for label in all_labels:
            f.write(label + "\n")

    print(
        f"Done. Saved {len(all_labels)} embeddings (shape: {embs.shape}) to {args.output}/",
        file=sys.stderr,
    )
    if short_count:
        print(f"Note: {short_count} sequences shorter than {args.min_len} nt", file=sys.stderr)
    if missing_annotation:
        print(
            f"Warning: {len(missing_annotation)} sequences skipped (no annotation): "
            + ", ".join(missing_annotation[:5])
            + ("..." if len(missing_annotation) > 5 else ""),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
