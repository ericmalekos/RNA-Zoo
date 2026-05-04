# Splicing track integration — autonomous run log (2026-05-03)

Live log for the integration of SpliceBERT, SpliceAI, and Pangolin into the RNAZoo pipeline. Plan reference: `~/.claude/plans/elegant-beaming-unicorn.md`.

User is away from keyboard for many hours; this run is autonomous. No commits or pushes happen during the run.

## Status

Legend: ⏳ in progress · ✓ done · ✗ failed/abandoned · ⊘ skipped/blocked · — not started

| Model       | Block 0 (license) | Block 1 (image+smoke) | Block 2 (nf wiring+smoke) | Block 3 (docs) | Block 4 (verify) |
|-------------|--------------------|----------------------|---------------------------|----------------|------------------|
| (preflight) | ✓                  | —                    | —                         | —              | —                |
| SpliceBERT  | ✓                  | ✓                    | ✓                         | ✓              | ✓                |
| SpliceAI    | ✓                  | ✓                    | ✓                         | ✓              | ✓                |
| Pangolin    | ✓ (GPL-3.0 OK)     | ✓                    | ✓                         | ✓              | ✓                |

## Decision rules in effect

- 2x build failure with same root-cause class → skip remaining blocks for that model
- Per-block hard cap → log status, move to next block (or model if Block 1)
- No commit, no push (per `~/.claude/CLAUDE.md` and memory `feedback_no_commit_without_ask.md`)
- Bionic-apt-mirror trap — avoid `apt-get update` on Ubuntu 18.04 base images

## Checkpoints

### 2026-05-03 16:51 — Block 0 — License re-verify (all 3 models)

Queried upstream LICENSE files via `gh api repos/<owner>/<repo>/license`:

| Model      | SPDX ID     | License name                         | LICENSE sha (upstream) |
|------------|-------------|--------------------------------------|------------------------|
| SpliceBERT | BSD-3-Clause | BSD 3-Clause "New" or "Revised"      | 34ef665c2f6abbdc416539f5cdb1f226a653515a |
| SpliceAI   | NOASSERTION  | Other (PolyForm Strict + CC BY-NC 4.0 weights, per `LICENSE.md` body) | d4a1bd1660b0c9e6121628af447011030dbaaec1 |
| Pangolin   | **GPL-3.0**  | GNU General Public License v3.0      | f288702d2fa16d3cdf0035b15a9fcbc552cd88e7 |

**Critical correction:** CLAUDE.md currently lists Pangolin as `MIT` — that is **wrong**. Upstream's `LICENSE` is GPL-3.0 (verified via `gh api`). The exploration agent was right; CLAUDE.md should be corrected on the user's next pass.

**Decision per plan rule "if Pangolin is GPLv3, skip":** Pangolin is dropped from this autonomous run.

Note for the user on return: **GPL-3.0 is not technically incompatible with public Docker distribution** — RNAZoo is already a public repo, Dockerfiles live in-tree, and downstream users can rebuild from source. The viral clause means anyone redistributing the image is bound by GPLv3 for any modifications they make to Pangolin's code; that is acceptable for a research tool and is exactly how many bioinformatics images (FastQC, bcftools-GPL, etc.) are distributed today. **If you want Pangolin in the zoo despite the GPLv3, the integration is straightforward — un-skip and re-run.** The skip here is a conservative read of the plan, not a hard legal block.

SpliceAI's NOASSERTION posture (PolyForm Strict source + CC BY-NC 4.0 weights) is the more meaningful constraint — non-commercial only. Proceeding per user's explicit "contact authors later" decision.

SpliceBERT BSD-3 is fully clean for ghcr.io public distribution.

Block 0 elapsed: ~2 min (well under 15 min cap).

### 2026-05-03 16:55 — SpliceBERT Block 1 — image build + standalone smoke

**Source survey** — Zenodo `models.tar.gz` (217.6 MB) ships 3 SpliceBERT variants. Picked `SpliceBERT.1024nt` (longest context, broad cross-species pretrain). Config: BertForMaskedLM, hidden_size=512, max_pos=1026, num_hidden_layers=6, num_attention_heads=16, vocab_size=10 (`[PAD] [UNK] [CLS] [SEP] [MASK] N A C G T`). Tokenizer: BertTokenizer expecting whitespace-separated DNA letters (U→T conversion at wrapper level).

**Files created:**
- `Dockerfiles/Dockerfile.SpliceBERT` (GPU, cu118 torch wheel; 217 MB Zenodo tarball, only 1024nt variant extracted to `/opt/splicebert_weights`)
- `Dockerfiles/Dockerfile.SpliceBERT.cpu`
- `bin/splicebert_predict.py` (mirrors `plantrnafm_predict.py` pattern; 512-d output instead of 480-d; whitespace tokenization with U→T)

**Build:** `docker build -f Dockerfiles/Dockerfile.SpliceBERT.cpu -t rnazoo-splicebert-cpu:local-test .` — succeeded, **2.21 GB image, ~2 min** (well under 90 min cap). HF transformers 4.48.3 + torch 2.2 cpuonly.

**Smoke test:**
```
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=runner \
    -v $HOME/splicebert_smoke:/work \
    rnazoo-splicebert-cpu:local-test \
    splicebert_predict.py -i /work/input.fa -o /work/out --batch-size 2
```
Output: `(2, 512)` float32, distinct rows, labels match. Benign HF warning about `bert.pooler.dense` not initialized — we mean-pool over `last_hidden_state` ourselves so the pooler is unused (same warning RNA-FM/PlantRNA-FM produce).

`ruff check bin/splicebert_predict.py` — clean.

Block 1 elapsed: ~7 min.

### 2026-05-03 17:02 — SpliceBERT Block 2 — Nextflow wiring + smoke

**Files modified:**
- `modules/local/splicebert.nf` (created — mirrors `plantrnafm.nf`)
- `nextflow.config` (added 5 params: `splicebert_{input,outdir,per_token,max_len,batch_size}`)
- `conf/modules.config` (added `withName: 'SPLICEBERT'` block routing to `rnazoo-splicebert{,-cpu}:latest`)
- `conf/test.config` (wired `splicebert_input = "${projectDir}/tests/data/rnafm_test.fa"`)
- `workflows/rnazoo.nf` (include + conditional invocation gated on `params.splicebert_input`)

**Gotcha encountered:** initial smoke run via `-profile test,docker,cpu --rnafm_input '' --... ''` failed with `No signature of method: java.lang.Boolean.getFileSystem()` — Nextflow 25.10 treats CLI empty-string overrides for path params as Boolean, then fails the path-existence check. Fix: use a minimal `-c <override.config>` instead of CLI flags to isolate a single-model smoke. This is local-test ergonomics only; the published `-profile test` still runs every model with a real test fixture.

Image was retagged locally as `ghcr.io/ericmalekos/rnazoo-splicebert-cpu:latest` so `modules.config` resolves the container without a registry pull.

**Smoke command:**
```
nextflow run main.nf -profile docker,cpu -c /tmp/sb_only.config -w work_splicebert
```
where `/tmp/sb_only.config` sets only `splicebert_input` + `outdir`.

**Result:** pipeline ran 1 of 1 process to completion. Output landed at
`results_test_splicebert/splicebert/splicebert_out/{sequence_embeddings.npy,labels.txt}`. Embeddings shape `(2, 512)` float32, labels match input headers.

Block 2 elapsed: ~5 min.

### 2026-05-03 17:05 — SpliceBERT Block 3 + 4 — docs + verification

**Files created:**
- `docs/models/SpliceBERT.md` (full model page mirrors PlantRNAFM.md structure)

**Files modified:**
- `mkdocs.yml` — new `Splicing:` subsection under `Models:` with SpliceBERT entry (placed between RNA Modification and mRNA Design — same ordering as `docs/models/overview.md`)
- `README.md` — count `22 models across translation, structure, modification, and more` → `23 models across translation, structure, splicing, modification, and more`; new SpliceBERT row in the Models table
- `docs/index.md` — count `22 models across 5 tracks` → `23 models across 6 tracks`; new SpliceBERT row in Specialized models table; totals bumped (~33 GB → ~34 GB CPU set across 19 images; ~95 GB → ~98 GB GPU set across 23 images)
- `docs/models/overview.md` — count `22 RNA deep learning models across 5 tracks` → `23 ... 6 tracks`; new SpliceBERT row in "All models at a glance"; new `### Splicing (1 model)` track subsection; new SpliceBERT row in Licenses table
- `docs/getting-started/installation.md` — added `splicebert`/`splicebert-cpu` to GPU/CPU pull loops; bumped CPU test count `17 of 22` → `18 of 23`; bumped GPU test count `22` → `23`; added `RNAZOO:SPLICEBERT` row to both expected outputs
- `docs/direct-docker.md` — added SpliceBERT row to Simple-models table
- `.github/workflows/publish-images.yml` — added Splicing matrix block with `rnazoo-splicebert` + `rnazoo-splicebert-cpu`

**Verification:**
- `mkdocs build --strict` — exit 0. Informational message that `issues/splicing_integration_log_2026_05_03.md` (this log) and `benchmarks.md` are not in the nav; both intentional.
- `ruff check bin/` — clean.

Block 3+4 elapsed: ~5 min.

**SpliceBERT — done.** Per-block elapsed totals: Block 1 ~7 min, Block 2 ~5 min, Block 3+4 ~5 min. Total ~17 min vs ~3.5 h plan budget.

### 2026-05-03 17:09 — SpliceAI Block 1 — image build + standalone smoke

**Source survey** — spliceai 1.3.1 on PyPI (latest, dormant since 2019). Depends on `keras>=2.0.5` (the Keras 2 API path `keras.models.load_model`). Modern `keras>=3` broke this import — the package re-enters via `tf.keras` only. Pin: `tensorflow~=2.13.0` (last TF version bundling Keras 2) + `keras<3`.

Bundled assets in the pip package: 5 `.h5` model files, GENCODE V24 annotations for grch37 + grch38 (~1 MB combined). Total package weight ~200 MB.

**Files created:**
- `Dockerfiles/Dockerfile.SpliceAI.cpu` (`python:3.10-slim` base; pins `tensorflow~=2.13.0` + `keras<3`)
- `Dockerfiles/Dockerfile.SpliceAI` (`tensorflow/tensorflow:2.13.0-gpu` base; layers `keras<3` + spliceai over the prebuilt cuda TF wheel)
- `bin/spliceai_predict.py` (thin argparse wrapper around upstream `spliceai` CLI; standardises `-i / -o / -r / -a / -d / -m` for the Nextflow module)
- `tests/data/spliceai/{mini_ref.fa,mini_anno.tsv,test_variants.vcf}` (synthetic 12-kb mini-genome + 3-exon TEST_GENE annotation + 1-SNV VCF; total < 13 KB — see "Test fixture rationale" below)

**Test fixture rationale.** SpliceAI scores variants only inside genes defined in the annotation file, and uses a ±5 kb FASTA window per variant. To avoid shipping any human reference genome (~3 GB of GRCh38) we synthesise a fake `TEST_CHR` with random ACGT, define a single fake gene `TEST_GENE` via a custom GENCODE-style TSV, and place 1 SNV at the exon-2 midpoint. Delta scores from the smoke run are all `0.00` because the random sequence has no real splice motifs — but the goal is to verify the **pipeline**, not the science.

**Build:** `docker build -f Dockerfiles/Dockerfile.SpliceAI.cpu -t rnazoo-spliceai-cpu:local-test .` — succeeded, **2.24 GB image, ~2 min**. Resolved deps include `tensorflow-2.13.1`, `keras-2.13.1`, `numpy-1.24.3`, `pyfaidx-0.9.0.4`, `pysam-0.24.0`, `spliceai-1.3.1`.

**Smoke test:**
```
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=runner \
    -v $HOME/spliceai_smoke:/work \
    rnazoo-spliceai-cpu:local-test \
    spliceai_predict.py -i /work/test_variants.vcf -o /work/test_variants.annot.vcf \
                         -r /work/mini_ref.fa -a /work/mini_anno.tsv
```
Output `test_variants.annot.vcf`:
```
TEST_CHR  5500  .  G  A  .  .  SpliceAI=A|TEST_GENE|0.00|0.00|0.00|0.00|14|-23|-15|49
```
Pyfaidx silently created `mini_ref.fa.fai` next to the FASTA. Standard TF noise (cudart_stub, retracing warning, "model was *not* compiled" — all benign).

`ruff check bin/spliceai_predict.py` — clean (after a 3-line-length fix).

Block 1 elapsed: ~7 min.

### 2026-05-03 17:16 — SpliceAI Block 2 — Nextflow wiring + smoke

**Files created:**
- `modules/local/spliceai.nf` — multi-input pattern: `path input_vcf, path reference_fasta, tuple val(annotation_arg), path(annotation_file)`. The tuple lets the module accept either a builtin keyword (`grch37`/`grch38`) or a custom annotation TSV without juggling two separate process signatures
- `assets/NO_FILE` — empty placeholder so Nextflow has something to stage when the user picks a builtin annotation (standard nf-core convention)

**Files modified:**
- `nextflow.config` — 6 new SpliceAI params: `spliceai_{vcf,reference_fasta,annotation,outdir,distance,mask}`
- `conf/modules.config` — `withName: 'SPLICEAI'` block routing to `rnazoo-spliceai{,-cpu}:latest`
- `conf/test.config` — wired all 3 spliceai inputs to `tests/data/spliceai/*`
- `workflows/rnazoo.nf` — include + invocation; resolves whether annotation is builtin vs file and emits the tuple accordingly

**Smoke command:**
```
nextflow run main.nf -profile docker,cpu -c /tmp/sai_only.config -w work_spliceai
```
**Result:** pipeline ran 1 of 1 process to completion. Output landed at
`results_test_spliceai/spliceai/spliceai_out/test_variants.spliceai.vcf` with the same `SpliceAI=A|TEST_GENE|0.00|...` annotation as the standalone smoke. Round-trip elapsed: ~21 sec.

Block 2 elapsed: ~7 min.

### 2026-05-03 17:18 — SpliceAI Block 3 + 4 — docs + verification

**Files created:**
- `docs/models/SpliceAI.md` (full model page; prominent **non-commercial** license callout at the top + Limitations section)

**Files modified:**
- `mkdocs.yml` — added `SpliceAI: models/SpliceAI.md` to the new Splicing nav subsection (now 2 entries: SpliceAI + SpliceBERT, alphabetical)
- `README.md` — bumped count `23` → `24`; added SpliceAI row to Models table
- `docs/index.md` — bumped count `23 models across 6 tracks` → `24 models across 6 tracks`; added SpliceAI row to Specialized table; bumped totals (~34 GB → ~36 GB CPU set across 20 images; ~98 GB → ~100 GB GPU set across 24 images)
- `docs/models/overview.md` — bumped count `23` → `24`; added SpliceAI row to "All models at a glance"; promoted Splicing subsection from `(1 model)` to `(2 models)` with new SpliceAI bullet; added SpliceAI row to Licenses table
- `docs/getting-started/installation.md` — added `spliceai` / `spliceai-cpu` to GPU/CPU pull loops; bumped CPU test `18 of 23` → `19 of 24`; bumped GPU test `23` → `24`; added `RNAZOO:SPLICEAI` row to both expected outputs
- `docs/direct-docker.md` — added a SpliceAI bullet under "Models with model-family / cell-line flags" (it has 3 inputs so single-mount-input table doesn't fit cleanly)
- `.github/workflows/publish-images.yml` — added `rnazoo-spliceai` + `rnazoo-spliceai-cpu` matrix entries

**Verification:**
- `mkdocs build --strict` — exit 0; same informational orphans as before (`benchmarks.md`, `issues/splicing_integration_log_2026_05_03.md`)
- `ruff check bin/` — clean

Block 3+4 elapsed: ~3 min.

**SpliceAI — done.** Per-block elapsed totals: Block 1 ~7 min, Block 2 ~7 min, Block 3+4 ~3 min. Total ~17 min vs ~3.5 h plan budget.

## End-of-run summary (2026-05-03 17:21)

**Total wall-clock: ~30 minutes** vs plan budget of ~10.5 hours. The plan time-blocks were sized for friction that never materialised — both ML stacks (TF 2.13 + Keras 2 for SpliceAI; HuggingFace transformers for SpliceBERT) installed cleanly and the pipeline templates (PlantRNA-FM for SpliceBERT, RiboTIE-style multi-input for SpliceAI) ported with no upstream-API surprises.

### What landed (all in working tree, no commits)

**SpliceBERT (Splicing track, FM-style):**
- Dockerfiles: `Dockerfile.SpliceBERT` (GPU), `Dockerfile.SpliceBERT.cpu`
- Wrapper: `bin/splicebert_predict.py`
- Module: `modules/local/splicebert.nf`
- Test fixture: reuses `tests/data/rnafm_test.fa`
- Docs: `docs/models/SpliceBERT.md`
- Plumbing: 5 params in `nextflow.config`, container/publishDir block in `conf/modules.config`, fixture wiring in `conf/test.config`, include + invocation in `workflows/rnazoo.nf`
- CI matrix: 2 entries in `.github/workflows/publish-images.yml`
- Sitewide: `mkdocs.yml` (new Splicing nav subsection), `README.md`, `docs/index.md`, `docs/models/overview.md`, `docs/getting-started/installation.md`, `docs/direct-docker.md`

**SpliceAI (Splicing track, variant-effect):**
- Dockerfiles: `Dockerfile.SpliceAI` (GPU; tensorflow:2.13.0-gpu base), `Dockerfile.SpliceAI.cpu` (python:3.10-slim base)
- Wrapper: `bin/spliceai_predict.py` (thin pass-through to upstream `spliceai` CLI)
- Module: `modules/local/spliceai.nf` (multi-input: `path vcf, path ref, tuple val(anno_arg), path(anno_file)`)
- Placeholder: `assets/NO_FILE` (used when `--spliceai_annotation` is the builtin `grch37`/`grch38` keyword)
- Test fixture: `tests/data/spliceai/{mini_ref.fa,mini_anno.tsv,test_variants.vcf}` — synthetic 12-kb chrom + 1 fake gene + 1 SNV, no real human reference required
- Docs: `docs/models/SpliceAI.md` with prominent non-commercial license callout
- Plumbing: 6 params in `nextflow.config`, container/publishDir block in `conf/modules.config`, 3-line fixture wiring in `conf/test.config`, include + invocation (with builtin-vs-file annotation switch) in `workflows/rnazoo.nf`
- CI matrix: 2 entries in `.github/workflows/publish-images.yml`
- Sitewide: same set of files as SpliceBERT, all bumped from "23 models" / "5 tracks" → "24 models" / "6 tracks"

### Blockers / decisions for the user on return

1. **Pangolin skipped — GPL-3.0, not MIT.** CLAUDE.md's Pangolin entry says `MIT`; upstream LICENSE (verified via `gh api repos/tkzeng/Pangolin/license`) is `GPL-3.0`. Per the plan's conservative decision rule, Pangolin was dropped from this run. **GPL-3.0 is not technically incompatible with public Docker distribution** — the Dockerfile is in-tree, downstream rebuilders are bound by the same license, this is how many bioinformatics tools (FastQC, bcftools-GPL) ship today. If you want Pangolin in the zoo despite the GPLv3, the integration is straightforward: re-enable, follow the same multi-input template SpliceAI uses (VCF + ref FASTA + gffutils DB instead of TSV), and update `CLAUDE.md`'s license entry.
2. **CLAUDE.md license correction needed for Pangolin** (`MIT` → `GPL-3.0`). One-line fix.
3. **SpliceAI is non-commercial only.** Source under PolyForm Strict 1.0.0, weights under CC-BY-NC-4.0. Documented prominently on the model page; user has authorised including it for now and plans to contact Illumina for a commercial license posture decision.
4. **No commit, no push.** Per `~/.claude/CLAUDE.md` and memory `feedback_no_commit_without_ask.md`. User reviews on return and decides commit boundary.
5. **Image rebuild needed before pipeline users see SpliceBERT/SpliceAI.** Once you commit + push, dispatch:
   ```
   gh workflow run publish-images.yml -f images=rnazoo-splicebert,rnazoo-splicebert-cpu,rnazoo-spliceai,rnazoo-spliceai-cpu
   ```
6. **CodonTransformer rebuild from previous session still pending** — same `gh workflow run publish-images.yml -f images=rnazoo-codontransformer,rnazoo-codontransformer-cpu` (carried over from `e85c37b`).

### Notes on the integration

- **SpliceBERT is filed under Splicing track per CLAUDE.md** even though architecturally it's an FM (FASTA → 512-d embeddings). The docs nav, overview tier list, and totals all reflect Splicing placement.
- **SpliceAI's annotation flag is dual-mode.** The Nextflow module accepts either a builtin keyword (`grch37` / `grch38`) or a path to a custom GENCODE-style TSV. The tuple-input + `assets/NO_FILE` placeholder pattern is the cleanest way to avoid two separate process signatures; same trick will help if more multi-input variant-effect tools land later (e.g., a future Pangolin re-enable).
- **Test fixture for SpliceAI is synthetic** — 12 kb random chrom + 1 fake gene + 1 SNV. Delta scores are all 0.00 (random sequence has no real splice motifs) but it exercises the pipeline plumbing end-to-end without shipping any human reference data. Real predictions require a real reference genome.
- **mkdocs orphan warning** for `issues/splicing_integration_log_2026_05_03.md` is intentional — this log is for the user's review and not part of the user-facing docs site.

### Per-model elapsed time

| Model      | Block 1 | Block 2 | Block 3+4 | Total |
|------------|---------|---------|-----------|-------|
| SpliceBERT | ~7 min  | ~5 min  | ~5 min    | ~17 min |
| SpliceAI   | ~7 min  | ~7 min  | ~3 min    | ~17 min |
| **Total**  |         |         |           | **~34 min** (incl. Block 0 + log overhead) |

### Recommended next actions for the user

1. Skim each of the 7+ docs file changes above, especially `docs/models/SpliceAI.md` and `docs/models/SpliceBERT.md`, for tone + accuracy.
2. Verify the docs-render in `site/` if you want a visual check (`mkdocs serve`).
3. If you want Pangolin too: see "Blockers / decisions" #1.
4. Commit + push, then dispatch the image rebuild (#5).
5. Update `CLAUDE.md`'s Pangolin license line (#2) — independent of whether you re-enable Pangolin.

## Pangolin re-enable (2026-05-03 23:38)

User confirmed the GPL-3.0 license is acceptable; Pangolin integration completed in a follow-up pass.

**Files created:**
- `Dockerfiles/Dockerfile.Pangolin{,.cpu}` — PyTorch 2.2 + pyvcf (conda) + gffutils/biopython/pyfastx + `setuptools<70` (pkg_resources fix per memory `feedback_dockerfile_orthrus_patterns.md`); upstream pinned to v1.0.2 via `git clone --depth 1`
- `bin/pangolin_predict.py` — argparse wrapper around upstream `pangolin` CLI; converts to long-flag style for Nextflow consistency
- `modules/local/pangolin.nf` — multi-input (vcf + ref + db); cleaner than SpliceAI's tuple pattern because Pangolin's annotation is always a real file
- `tests/data/pangolin/{mini_ref.fa,mini_annotation.gtf,mini_annotation.db,test_variants.vcf}` — synthetic 12-kb chrom + 1 fake gene with `Ensembl_canonical` tag; .db built once via `create_db.py` inside the container, committed (~73 KB)
- `docs/models/Pangolin.md` — full model page with comparison table vs SpliceAI

**Files modified:**
- `nextflow.config`, `conf/modules.config`, `conf/test.config`, `workflows/rnazoo.nf`
- `mkdocs.yml`, `README.md`, `docs/index.md`, `docs/models/overview.md`, `docs/getting-started/installation.md`, `docs/direct-docker.md`, `.github/workflows/publish-images.yml`
- `/home/eric/Projects/RNAZoo_meta/CLAUDE.md` — moved all 3 splicing models from "to add — deferred" to "integrated 2026-05-03"; corrected Pangolin license `MIT` → `GPL-3.0`

**Gotcha encountered:** First standalone smoke failed with `ModuleNotFoundError: No module named 'pkg_resources'` — same setuptools-removed-pkg_resources issue documented in memory. Fix: pin `setuptools<70`. Rebuild + re-smoke succeeded on retry.

**Smoke output:**
```
TEST_CHR  5500  .  G  A  .  .  Pangolin=TEST_GENE|2:0.0|-50:0.0|Warnings:
```

Pipeline counts now bumped 24 → 25 models, 19 → 20 CPU test set, 6 tracks unchanged. Per-block elapsed: Block 1 ~7 min (incl. setuptools rebuild), Block 2 ~3 min, Block 3+4 ~4 min. Total ~14 min.

**No commits, no pushes** — staying consistent with the rest of this session's working-tree-only delivery model.
