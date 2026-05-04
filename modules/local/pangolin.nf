/*
========================================================================================
    PANGOLIN module: variant-effect splicing prediction (tissue-specific)
    Upstream: https://github.com/tkzeng/Pangolin
    Paper: Zeng & Li, Genome Biology 2022 (10.1186/s13059-022-02664-4)
    License: GPL-3.0
    Inputs:
      - VCF or CSV of variants
      - Reference FASTA (gzipped accepted; pyfastx auto-indexes)
      - gffutils annotation DB (built from a GTF via upstream `create_db.py`)
    Output: annotated VCF/CSV with `Pangolin=...` INFO field (gene|pos:Δ_inc|pos:Δ_dec|warnings)
========================================================================================
*/

process PANGOLIN {
    tag "pangolin"
    label 'process_medium'

    input:
    path input_variants
    path reference_fasta
    path annotation_db

    output:
    path "pangolin_out/*", emit: predictions

    script:
    def basename = input_variants.getBaseName()
    def score_arg = params.pangolin_score_cutoff != null ? "-s ${params.pangolin_score_cutoff}" : ''
    def column_arg = params.pangolin_column_ids ? "-c ${params.pangolin_column_ids}" : ''
    """
    mkdir -p pangolin_out
    pangolin_predict.py \
        -i ${input_variants} \
        -r ${reference_fasta} \
        -a ${annotation_db} \
        -o pangolin_out/${basename}.pangolin \
        -d ${params.pangolin_distance} \
        -m ${params.pangolin_mask} \
        ${score_arg} \
        ${column_arg}
    """
}
