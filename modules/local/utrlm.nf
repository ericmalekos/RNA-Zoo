/*
========================================================================================
    UTRLM module: predict 5'UTR expression metrics (MRL, TE, EL)
    Upstream: https://github.com/a96123155/UTR-LM
    Paper: Nature Machine Intelligence 2024
    Input: FASTA of 5'UTR DNA sequences
    Output: predictions.tsv with per-sequence metric predictions
========================================================================================
*/

process UTRLM {
    tag "utrlm:${params.utrlm_task}"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "utrlm_out/predictions.tsv", emit: predictions

    script:
    def cell_line_flag = params.utrlm_task != 'mrl' ? "--cell-line ${params.utrlm_cell_line}" : ''
    def ckpt_flag = params.utrlm_checkpoint ? "--checkpoint ${params.utrlm_checkpoint}" : ''
    """
    utrlm_predict.py \
        -i ${input_fasta} \
        -o utrlm_out \
        --task ${params.utrlm_task} \
        ${cell_line_flag} \
        ${ckpt_flag} \
        --model-dir /opt/utrlm/Model
    """
}
