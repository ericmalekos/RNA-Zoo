# DRfold2

Single-sequence ab initio RNA 3D structure prediction with a composite RNA language model + denoised end-to-end learning. Tier-2 structure model alongside RhoFold; DRfold2 wins on novel-fold cases and matches AlphaFold3 on several benchmarks at ~10⁵× lower cost than fragment-assembly approaches like FarFar2/SimRNA.

- **Paper:** [Li et al. 2025 (preprint, "Ab initio RNA structure prediction with composite language model and denoised end-to-end learning")](https://github.com/leeyang/DRfold2)
- **GitHub:** [`leeyang/DRfold2`](https://github.com/leeyang/DRfold2)
- **License:** MIT (declared in upstream README body; **no LICENSE file on the repo** — flagged for redistribution review). Bundled `Arena` refinement utility (cloned from [pylelab/Arena](https://github.com/pylelab/Arena)) has **no declared license** on its upstream — see "Limitations" below.
- **Device:** GPU only. Auto-skipped under `-profile cpu` with a warning.
    - `rnazoo-drfold2:latest` — single image; ~5 GB compressed
    - No CPU image (the 4-model ensemble + IPA + Arena refinement is not feasible on CPU)

## What it does

DRfold2 predicts atomic 3D structure from a single RNA sequence — no MSA, no template, no co-evolution from sister sequences. The pipeline is:

1. **Composite RNA language model (RCLM)** approximates full-likelihood co-evolutionary signal from unsupervised single-sequence input.
2. **4-model deep-learning ensemble** (`cfg_95`, `cfg_96`, `cfg_97`, `cfg_99`) generates candidate end-to-end structures and pairwise geometries.
3. **Selection.py** picks the best candidate; **Optimization.py** refines geometry with IPA (invariant point attention).
4. **Arena** (a vendored C-compiled chain refinement utility from `pylelab/Arena`) does coarse-to-atomic backbone reconstruction.
5. **Optional clustering pass** (`--cluster`) re-runs Selection+Optimization+Arena on alternative ensemble members to emit `model_2.pdb`, `model_3.pdb`, … alongside the primary `model_1.pdb`.

The final output is one PDB per input sequence.

## Input format

Standard FASTA of RNA sequences (A/C/G/U; T accepted and converted internally). The wrapper iterates per record — each sequence runs as a separate DRfold2 invocation in a fresh per-sequence work dir.

Example smoke fixture (`tests/data/drfold2_test.fa`, 24-nt UUCG hairpin):

```
>uucg_hairpin
GAGCGGCAUCUUCGGAUGCCGCUC
```

## Output format

A directory containing:

- **`<safe_label>.pdb`**: one PDB file per input sequence (the top-selected DRfold2 model — equivalent to upstream's `relax/model_1.pdb`)
- With `--drfold2_cluster`: additional `<safe_label>_alt2.pdb`, `<safe_label>_alt3.pdb`, … from the clustering pass

Per-sequence intermediate dirs (`rets_dir/`, `folds/`, `relax/`) are removed by default — pass `--drfold2_keep_intermediate` to retain them (can be many GB for longer sequences).

## Run with Docker

```bash
# GPU only (no CPU image)
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -u $(id -u):$(id -g) \
  -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-drfold2:latest \
  drfold2_predict.py -i /data/input.fa -o /out
```

Add `--cluster` for alternative-conformation models, `--keep-intermediate` to preserve working dirs.

## Run with Nextflow

```bash
# GPU only — DRfold2 auto-skips under -profile cpu
nextflow run main.nf -profile docker,gpu --drfold2_input /path/to/input.fa
```

Results land in `results/drfold2/drfold2_out/`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--drfold2_cluster` | `false` | Run additional clustering pass (emits `<label>_alt2.pdb`, …) |
| `--drfold2_keep_intermediate` | `false` | Retain per-sequence working dirs |

## Reading the output

PDB files are standard format — open in PyMOL, ChimeraX, or `Bio.PDB`:

```python
from Bio.PDB import PDBParser
parser = PDBParser(QUIET=True)
struct = parser.get_structure("uucg_hairpin", "drfold2_out/uucg_hairpin.pdb")
for atom in struct.get_atoms():
    print(atom.element, atom.coord)
```

## Comparison with the other structure models in the zoo

| Model | Output | Method | MSA / template | Speed (per sequence) | License |
|-------|--------|--------|----------------|----------------------|---------|
| [RNAformer](RNAformer.md) | 2D dot-bracket + base-pair matrix | Transformer with recycling | None | < 1 s | Apache-2.0 |
| [SPOT-RNA](SPOTRNA.md) | 2D bpseq/CT (incl pseudoknots) | 5-model TF ensemble | None | ~ 1 s | MPL-2.0 |
| [RhoFold](RhoFold.md) | 3D PDB | E2E + AmberRelax (single-seq mode) | None | ~ 5 min on CPU, < 1 min on GPU | Apache-2.0 |
| **DRfold2** | **3D PDB** | **4-model ensemble + IPA + Arena** | **None** | **~ 10-30 min for 30 nt; 40-120 min for typical RNAs** | **MIT** |

DRfold2's headline: it beats RhoFold/RoseTTAFoldNA/DeepFoldRNA on a 41-target TM-score benchmark (0.350 vs 0.292 next-best) and edges AlphaFold3 on novel folds. Top-L contact precision 49.0% vs RNA-FM 23.6% / RiNALMo 24.0%. Pseudoknot recovery 56% vs AF3 79%. Caveat: only 24% of benchmark targets clear TM≥0.45 (the structural-match threshold), so absolute accuracy on out-of-distribution RNAs is still poor in absolute terms — DRfold2 is a relative state-of-the-art, not a solved-problem tool.

For most use cases, **start with RhoFold** (faster, simpler, smaller image) and reach for DRfold2 when RhoFold's output is unsatisfactory or for sequences where co-evolution-free 3D prediction matters (novel folds, designed RNAs).

## Limitations

- **GPU-only.** The 4-model ensemble + IPA + Arena pipeline is impractical on CPU. Auto-skipped under `-profile cpu` with a warning.
- **Slow.** ~10-30 min for short (24 nt) sequences on a consumer GPU (GTX 1650 Ti class), 40-120 min for typical 50-200 nt RNAs. Optional refinement (via OpenMM, not exposed in this wrapper) adds another ~180 min.
- **Memory.** Large ensemble + IPA may require >4 GB VRAM for sequences > 50 nt. Consumer GPUs may OOM on long inputs.
- **Bundled Arena license.** Arena (cloned from `pylelab/Arena` at build time) has **no declared license** on its upstream repo. The DRfold2 image as built can be used locally, but the project should not push it to a public registry until Arena's license is clarified or replaced. See `docs/DRfold2-issues/arena-license.md` for the redistribution decision log if you need to ship this image externally.
- **MIT license declared in README only.** DRfold2's repo has no LICENSE file; the MIT terms appear in the README body. GitHub's API reports it as `NO_LICENSE`. The README declaration is enforceable but unconventional — flag before commercial use.
- **Inference-only.** No fine-tuning support exposed.
