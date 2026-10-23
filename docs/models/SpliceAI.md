# SpliceAI

Predict the effect of genetic variants on RNA splicing.

- **Paper:** [Cell 2019](https://doi.org/10.1016/j.cell.2018.12.015)
- **Upstream:** https://github.com/Illumina/SpliceAI
- **License:** The image installs SpliceAI 1.3.1 from PyPI. At that release the source is GPL-3.0-or-later and the model weights carry no license statement. The current upstream repository is under [PolyForm Strict 1.0.0](https://github.com/Illumina/SpliceAI/blob/master/LICENSE) (non-commercial) and states that the weights are CC BY-NC 4.0. Commercial users should obtain a license from Illumina. The RNA-Zoo image is redistributed with the permission of the model's authors; anyone using it is bound by these terms.
- **Device:** CPU or GPU (images `rnazoo-spliceai-cpu` and `rnazoo-spliceai`).

## What it does

SpliceAI is a residual network of 32 dilated convolutions that reads 5,000 nt on each side of
every scored position; five models are averaged. It scores how much a variant raises or lowers
the use of nearby positions as splice acceptors and donors.

## Input

1. A VCF of variants.
2. A reference FASTA. A `.fai` index beside it is used if present; otherwise one is built in the
   work directory on each run.
3. A gene annotation: `grch37` (bundled GENCODE V24lift37 canonical transcripts), `grch38`
   (bundled GENCODE V24 canonical transcripts), or a custom tab-separated file with the columns
   `#NAME CHROM STRAND TX_START TX_END EXON_START EXON_END` and exon coordinates comma-separated
   with a trailing comma, as in upstream's `spliceai/annotations/grch37.txt`.

Example (upstream `examples/input.vcf`, GRCh37, annotation `grch37`):

```
##fileformat=VCFv4.2
##contig=<ID=19,length=59128983>
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
19	38958362	.	C	T	.	.	.
```

## Output

`spliceai_out/<input name>.spliceai.vcf`: the input records, with a `SpliceAI` INFO entry for
each scored allele and gene, `ALLELE|SYMBOL|DS_AG|DS_AL|DS_DG|DS_DL|DP_AG|DP_AL|DP_DG|DP_DL`.
The delta scores (0 to 1) cover acceptor gain, acceptor loss, donor gain and donor loss; the
delta positions place each change relative to the variant (positive is downstream). Upstream
reads the largest delta score as the probability that the variant alters splicing; the paper
characterizes cutoffs of 0.2 (high recall), 0.5 (recommended) and 0.8 (high precision).

Example (upstream `examples/output.vcf`):

```
19	38958362	.	C	T	.	.	SpliceAI=T|RYR1|0.00|0.00|0.91|0.08|-28|-46|-2|-31
```

## Run with Docker

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/inputs:/work \
  ghcr.io/ericmalekos/rnazoo-spliceai-cpu:latest \
  spliceai_predict.py -i /work/variants.vcf -o /work/variants.spliceai.vcf \
    -r /work/genome.fa -a grch38
```

For the GPU image, use `rnazoo-spliceai:latest` and add `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`.
A custom annotation goes in `/work` (`-a /work/annotation.tsv`); `-d` and `-m` set the distance
and the mask.

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --spliceai_vcf /path/to/variants.vcf \
  --spliceai_reference_fasta /path/to/genome.fa \
  --spliceai_annotation grch38
```

Use `-profile docker,gpu` for the GPU image. Results go to `results/spliceai/spliceai_out/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--spliceai_vcf` | `null` | Input VCF |
| `--spliceai_reference_fasta` | `null` | Reference FASTA; required |
| `--spliceai_annotation` | `grch38` | `grch37`, `grch38` or the path to a custom annotation file |
| `--spliceai_distance` | `50` | Maximum distance (0 to 4999) between the variant and a gained or lost splice site |
| `--spliceai_mask` | `0` | `1` sets gains at annotated sites and losses at unannotated sites to 0; upstream recommends `1` for variant interpretation, `0` for alternative splicing analysis |

## Limitations

- Only SNVs and simple indels (REF or ALT a single base) get scores. Other REF and ALT pairs get
  an entry of dots; symbolic, missing and `*` alleles get none.
- Records get no `SpliceAI` field when the variant is outside every annotated gene, within 5 kb
  of a chromosome end, has a REF allele longer than twice `--spliceai_distance`, or does not
  match the reference FASTA.
