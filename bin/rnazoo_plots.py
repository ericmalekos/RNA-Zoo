#!/usr/bin/env python3
"""
Shared plotting utilities for RNAZoo model outputs.
All functions save PNGs and gracefully skip if matplotlib is unavailable.
"""

import sys

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def check_matplotlib():
    if not HAS_MPL:
        print(
            "Warning: matplotlib not available, skipping plots",
            file=sys.stderr,
        )
    return HAS_MPL


def plot_contact_map(prob_matrix, sequence, header, outpath, title_prefix=""):
    """Plot an L×L base-pair probability heatmap."""
    if not check_matplotlib():
        return
    L = len(sequence)
    mat = prob_matrix[:L, :L]

    fig, ax = plt.subplots(figsize=(max(6, L / 15), max(6, L / 15)))
    im = ax.imshow(mat, cmap="YlOrRd", vmin=0, vmax=1, origin="upper")
    ax.set_xlabel("Position")
    ax.set_ylabel("Position")
    title = f"{title_prefix}{header}" if title_prefix else header
    ax.set_title(f"{title} ({L} nt)", fontsize=10)
    plt.colorbar(im, ax=ax, label="Base-pair probability", shrink=0.8)

    # Add sequence labels on axes for short sequences
    if L <= 100:
        ax.set_xticks(range(0, L, max(1, L // 20)))
        ax.set_yticks(range(0, L, max(1, L // 20)))

    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()


def plot_modification_heatmap(scores_df, header, outpath, mod_names=None):
    """Plot a modification-type × position heatmap for one sequence."""
    if not check_matplotlib():
        return
    if mod_names is None:
        mod_names = [
            "Am", "Cm", "Gm", "Um", "m1A", "m5C",
            "m5U", "m6A", "m6Am", "m7G", "Psi", "AtoI",
        ]

    # scores_df: rows = positions, columns = modification types
    mat = scores_df[mod_names].values.T  # (12, L)
    positions = scores_df["position"].values
    bases = scores_df["base"].values
    L = len(positions)

    fig_width = max(8, L / 8)
    fig, ax = plt.subplots(figsize=(fig_width, 4))
    im = ax.imshow(mat, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)
    ax.set_yticks(range(len(mod_names)))
    ax.set_yticklabels(mod_names, fontsize=8)
    ax.set_xlabel("Position")
    ax.set_title(f"{header} ({L} positions)", fontsize=10)

    # Position labels
    if L <= 80:
        ax.set_xticks(range(L))
        ax.set_xticklabels(
            [f"{p}\n{b}" for p, b in zip(positions, bases, strict=True)],
            fontsize=5, rotation=0,
        )
    else:
        step = max(1, L // 30)
        ax.set_xticks(range(0, L, step))
        ax.set_xticklabels(positions[::step], fontsize=7)

    plt.colorbar(im, ax=ax, label="Probability", shrink=0.8)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()


def plot_ribosome_density(densities, header, outpath):
    """Plot per-codon ribosome density as a line plot."""
    if not check_matplotlib():
        return
    L = len(densities)

    # Cap width at 24 inches to avoid absurdly wide PNGs for long transcripts
    fig, ax = plt.subplots(figsize=(min(24, max(8, L / 20)), 4))
    ax.plot(range(1, L + 1), densities, linewidth=0.8, color="#2166ac")
    ax.fill_between(
        range(1, L + 1), densities, alpha=0.3, color="#2166ac",
    )
    ax.set_xlabel("Codon position")
    ax.set_ylabel("Predicted ribosome density")
    ax.set_title(f"{header} ({L} codons)", fontsize=10)
    ax.set_xlim(1, L)

    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
