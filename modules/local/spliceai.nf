/*
========================================================================================
    SPLICEAI module: variant-effect splicing prediction
    Upstream: https://github.com/Illumina/SpliceAI
    Paper: Jaganathan et al., Cell 2019 (10.1016/j.cell.2018.12.015)
    License: release 1.3.1 is GPL-3.0-or-later and states no license for the weights;
             later upstream releases use PolyForm Strict 1.0.0 and CC BY-NC 4.0
             (see docs/models/SpliceAI.md)
    Inputs:
      - VCF of variants
      - Reference FASTA, with its .fai staged when one exists beside it (built in the
        work directory otherwise)
      - Annotation: 'grch37' / 'grch38' (bundled GENCODE V24) OR a path to a custom TSV
    Output: annotated VCF with SpliceAI INFO field
========================================================================================
*/

process SPLICEAI {
    tag "spliceai"
    label 'process_medium'

    input:
    path input_vcf
    path reference_fasta
    path reference_fai      // <fasta>.fai staged beside the FASTA, or NO_FILE_FAI
    tuple val(annotation_arg), path(annotation_file)

    output:
    path "spliceai_out/*.spliceai.vcf", emit: annotated_vcf

    script:
    def basename = input_vcf.getBaseName()
    // If a real annotation file was staged (not the NO_FILE placeholder),
    // pass its staged name; otherwise pass the builtin keyword as-is.
    def anno_arg = annotation_file.name == 'NO_FILE' ? annotation_arg : annotation_file.name
    """
    mkdir -p spliceai_out
    spliceai_predict.py \
        -i ${input_vcf} \
        -o spliceai_out/${basename}.spliceai.vcf \
        -r ${reference_fasta} \
        -a ${anno_arg} \
        -d ${params.spliceai_distance} \
        -m ${params.spliceai_mask}
    """
}
