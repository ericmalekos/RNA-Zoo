/*
========================================================================================
    MULTIRM module: predict 12 RNA modification types from sequence
    Upstream: https://github.com/Tsedao/MultiRM
    Paper: NAR 2021
    Input: FASTA of RNA sequences (min 51 nt)
    Output: per-position modification probabilities + significant sites
========================================================================================
*/

process MULTIRM {
    tag "multirm"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "multirm_out/modification_scores.tsv", emit: scores
    path "multirm_out/predicted_sites.tsv",     emit: sites

    script:
    """
    multirm_predict.py \
        -i ${input_fasta} \
        -o multirm_out \
        --alpha ${params.multirm_alpha}
    """
}
