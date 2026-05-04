# Pangolin

Predict the effect of genetic variants on splice site strength, with tissue-specific scores.

- **Paper:** [Genome Biology 2022](https://doi.org/10.1186/s13059-022-02664-4) — Zeng & Li, "Predicting RNA splicing from DNA sequence using Pangolin"
- **Upstream:** [github.com/tkzeng/Pangolin](https://github.com/tkzeng/Pangolin)
- **License:** [GPL-3.0](https://github.com/tkzeng/Pangolin/blob/main/LICENSE) — copyleft. Public Docker distribution is permitted (the Dockerfile lives in this repo and downstream rebuilders are bound by the same license); commercial users should review the GPLv3 redistribution clauses for their use case.
- **Device:** CPU or GPU. Two image variants:
    - `rnazoo-pangolin:latest` — CUDA-enabled (default, used with `-profile gpu`)
    - `rnazoo-pangolin-cpu:latest` — CPU-only (smaller, used with `-profile cpu`)

## What it does

Pangolin is a deep-learning splice-site predictor that scores changes in splice site strength caused by SNVs and short indels. It improves on SpliceAI by training across **four tissues** (heart, liver, brain, testis from human + mouse + rhesus + rat), producing tissue-aware predictions rather than a single human-canonical score. Each variant gets two summary scores: the largest score *increase* and the largest score *decrease* within ±D bases (default D=50).

The pipeline currently exposes only the inference path. Upstream's `custom_usage.py` for arbitrary-sequence scoring is not yet wired in.

## Input format

Three inputs are required:

1. **Variants** — VCF or CSV. CSV must have a header with columns identifying CHROM/POS/REF/ALT (defaults `CHROM,POS,REF,ALT`; override via `--pangolin_column_ids "Chr,Pos,Ref,Alt"`).
2. **Reference FASTA** — any indexable format pyfastx supports (uncompressed `.fa`, bgzipped `.fa.gz` with `.gzi`, etc.). pyfastx auto-creates an index on first read.
3. **gffutils annotation database** — a `.db` file built from a GTF using upstream's `scripts/create_db.py`:

```bash
# inside the pangolin container, or any env with gffutils installed
python /opt/conda/envs/pangolin/bin/create_db.py gencode.v38.annotation.gtf.gz
# produces gencode.v38.annotation.db
```

Pre-built DBs for GENCODE 38 are available from the upstream Dropbox link in the [Pangolin README](https://github.com/tkzeng/Pangolin#installation). Variants are skipped if they're outside any annotated gene, within 5 kb of chromosome ends, deletions longer than `2 × distance`, or inconsistent with the reference FASTA.

Example VCF:

```
##fileformat=VCFv4.2
##contig=<ID=chr19,length=58617616>
#CHROM  POS       ID  REF  ALT  QUAL  FILTER  INFO
chr19   38958362  .   C    T    .     .       .
```

## Output format

An annotated VCF (or CSV, matching the input) where each record gains a `Pangolin=...` field in `INFO`:

```
chr19  38958362  .  C  T  .  .  Pangolin=RYR1|2:0.91|-31:-0.08|Warnings:
```

Format: `gene_symbol|relpos:largest_increase|relpos:largest_decrease|Warnings:<msg>`. Position offsets are relative to the variant POS.

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
# CPU
docker run --rm \
  -v /path/to/inputs:/work \
  ghcr.io/ericmalekos/rnazoo-pangolin-cpu:latest \
  pangolin_predict.py \
    -i /work/variants.vcf \
    -r /work/genome.fa \
    -a /work/annotation.db \
    -o /work/variants.pangolin

# GPU
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/inputs:/work \
  ghcr.io/ericmalekos/rnazoo-pangolin:latest \
  pangolin_predict.py \
    -i /work/variants.vcf \
    -r /work/genome.fa \
    -a /work/annotation.db \
    -o /work/variants.pangolin
```

The output prefix is `variants.pangolin`; Pangolin auto-appends `.vcf` (or `.csv`) matching the input.

## Run with Nextflow

```bash
# CPU
nextflow run main.nf -profile docker,cpu \
  --pangolin_variants /path/to/variants.vcf \
  --pangolin_reference_fasta /path/to/genome.fa \
  --pangolin_annotation_db /path/to/annotation.db

# GPU
nextflow run main.nf -profile docker,gpu \
  --pangolin_variants /path/to/variants.vcf \
  --pangolin_reference_fasta /path/to/genome.fa \
  --pangolin_annotation_db /path/to/annotation.db
```

Only models with input provided will run — no ignore flags needed.

Results appear in `results/pangolin/pangolin_out/<basename>.pangolin.vcf` (or `.csv`).

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--pangolin_variants` | (required) | VCF or CSV with variants |
| `--pangolin_reference_fasta` | (required) | Reference FASTA (auto-indexed by pyfastx) |
| `--pangolin_annotation_db` | (required) | gffutils annotation DB (built via `scripts/create_db.py`) |
| `--pangolin_distance` | `50` | Bases on either side of the variant for splice-score calculation |
| `--pangolin_mask` | `'True'` | Mask annotated-site gain + unannotated-site loss (recommended for variant interpretation) |
| `--pangolin_score_cutoff` | `null` | If set, output every site with `\|delta\| ≥ cutoff` instead of just the max-loss/gain |
| `--pangolin_column_ids` | `null` | (CSV input only) comma-separated column names for CHROM,POS,REF,ALT — upstream default `'CHROM,POS,REF,ALT'` is used when this is unset |

## Reading the output

```python
import pysam

vcf = pysam.VariantFile("variants.pangolin.vcf")
for rec in vcf:
    info = rec.info.get("Pangolin")
    if not info:
        continue
    for entry in info:
        # gene|relpos:largest_inc|relpos:largest_dec|Warnings:...
        gene, inc, dec, *_ = entry.split("|")
        inc_pos, inc_score = inc.split(":")
        dec_pos, dec_score = dec.split(":")
        if abs(float(inc_score)) >= 0.5 or abs(float(dec_score)) >= 0.5:
            print(f"{rec.chrom}:{rec.pos} ({gene}) splice-altering: +{inc_score}@{inc_pos} / {dec_score}@{dec_pos}")
```

## Comparison with SpliceAI

| Aspect | SpliceAI | Pangolin |
|--------|----------|----------|
| Training | Human only (GTEx) | Human + mouse + rhesus + rat across 4 tissues |
| Outputs | 4 deltas (acceptor/donor × gain/loss) | 2 summary deltas (max increase, max decrease) |
| Annotation | Bundled GENCODE V24 OR custom TSV | gffutils DB (must build yourself via `create_db.py` or download upstream) |
| License | PolyForm Strict + CC-BY-NC-4.0 (non-commercial) | GPL-3.0 (copyleft) |
| Reference fmt | Plain FASTA + .fai | pyfastx-indexable (incl. bgzip + .gzi) |

Pangolin and SpliceAI are complementary — for a variant of interest, running both is common practice and disagreements between them often flag interesting biology.

## Test fixture (synthetic mini-genome)

The bundled smoke fixture under `tests/data/pangolin/` is the same shape as the SpliceAI fixture: a synthetic 12-kb chromosome (`TEST_CHR`) with random ACGT, a single fake `TEST_GENE` with 3 exons, and a single SNV. The fixture also ships the pre-built `mini_annotation.db` (~73 KB) so the Nextflow smoke doesn't need to call `create_db.py` at runtime. Delta scores from this fixture are 0.0 (random sequence has no splice motifs); the test verifies pipeline plumbing only.

## Limitations

- **GPL-3.0 copyleft.** If you ship downstream Docker images that modify Pangolin, you must release source under the same license.
- **Annotation DB is not bundled.** Unlike SpliceAI, Pangolin requires a user-supplied gffutils DB. For real-world use, download a pre-built GENCODE DB from the upstream Dropbox link or build your own from a GTF.
- **Variants must be inside annotated genes.** Same exclusion rules as SpliceAI: intergenic variants, variants within 5 kb of chromosome ends, and deletions longer than `2 × distance` are silently skipped.
- **No tissue selection in the wrapper.** The upstream model emits scores for 4 tissues; the bundled CLI summarises them into the max-increase / max-decrease pair. Per-tissue access would need a custom invocation.
