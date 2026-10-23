# Pangolin

Predict how genetic variants change splice-site strength, with models trained on four tissues.

- **Paper:** [Genome Biology 2022](https://doi.org/10.1186/s13059-022-02664-4)
- **Upstream:** https://github.com/tkzeng/Pangolin
- **License:** [GPL-3.0](https://github.com/tkzeng/Pangolin/blob/main/LICENSE), a copyleft license, for the code and the models it ships. Public Docker distribution is permitted (the Dockerfile is in this repository, and rebuilders are bound by the same license); commercial users should review the GPL-3.0 redistribution clauses for their use.
- **Device:** CPU or GPU (images `rnazoo-pangolin-cpu` and `rnazoo-pangolin`).

## What it does

Pangolin is a dilated residual convolutional network trained on splice-site usage from RNA-seq
of heart, liver, brain and testis in human, rhesus macaque, mouse and rat. Twelve models (three
per tissue) read 5,000 nt on each side of a variant and score each position within
`--pangolin_distance` of it; each position keeps its largest change across tissues.

## Input

1. Variants: a VCF, or a CSV with a header row and the columns `CHROM,POS,REF,ALT` (other names
   via `--pangolin_column_ids`). The file name must end in `.vcf` or `.csv`; compressed files
   are not read.
2. A reference FASTA, plain or gzipped. Pangolin reads it with pyfastx, which builds its own index.
3. A gffutils annotation database, built once from a GTF with upstream's `create_db.py`, which
   the image includes:

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/gtf_dir:/work \
  ghcr.io/ericmalekos/rnazoo-pangolin-cpu:latest \
  python /opt/conda/envs/pangolin/bin/create_db.py /work/gencode.v38.annotation.gtf.gz
# writes /work/gencode.v38.annotation.db
```

By default `create_db.py` keeps only transcripts tagged `Ensembl_canonical` (`--filter None`
keeps all). The [upstream README](https://github.com/tkzeng/Pangolin) links prebuilt GENCODE
release 38 databases for GRCh38 and GRCh37.

Example VCF (upstream `examples/brca.vcf`, GRCh37):

```
##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
chr17	41276135	.	T	G	.	.	.
```

## Output

`pangolin_out/<input name>.pangolin.vcf` (or `.csv`): the input, with a `Pangolin` INFO field
(VCF) or column (CSV) holding one entry per overlapping gene,
`gene_id|pos:largest_increase|pos:largest_decrease|Warnings:`. Positions are relative to the
variant. With `--pangolin_score_cutoff`, every position whose change reaches the cutoff is
listed instead of the largest two.

Example (a ZEB2 variant from a GRCh38 CSV run with `--pangolin_distance 500`; scores are rounded
to two decimals but can print with extra digits):

```
CHROM,POS,REF,ALT,Pangolin
chr2,144401198,C,T,ENSG00000169554.24|-12:0.5299999713897705|1:-0.8600000143051147|Warnings:
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/inputs:/work \
  ghcr.io/ericmalekos/rnazoo-pangolin-cpu:latest \
  pangolin_predict.py -i /work/variants.vcf -r /work/genome.fa \
    -a /work/annotation.db -o /work/variants.pangolin
```

For the GPU image, use `rnazoo-pangolin:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
Pangolin adds `.vcf` or `.csv` to the output prefix.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --pangolin_variants /path/to/variants.vcf \
  --pangolin_reference_fasta /path/to/genome.fa \
  --pangolin_annotation_db /path/to/annotation.db
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/pangolin/pangolin_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--pangolin_variants` | `null` | VCF or CSV of variants |
| `--pangolin_reference_fasta` | `null` | Reference FASTA; required |
| `--pangolin_annotation_db` | `null` | gffutils database; required |
| `--pangolin_distance` | `50` | Positions scored on each side of the variant |
| `--pangolin_mask` | `'True'` | `True` sets gains at annotated sites and losses at unannotated sites to 0 |
| `--pangolin_score_cutoff` | `null` | List every position with an absolute change at or above this value |
| `--pangolin_column_ids` | `null` | CSV only: chromosome, position, REF and ALT column names (`CHROM,POS,REF,ALT` when unset) |

## Limitations

- Only substitutions and simple indels (REF or ALT a single base) are scored, and in a VCF only
  the first ALT allele of each record.
- Variants get no scores when they lie outside annotated genes, within 5,000 nt of a chromosome
  end, are deletions longer than twice `--pangolin_distance`, or do not match the reference.
- Scores are not reported per tissue.
