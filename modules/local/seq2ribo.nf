/*
========================================================================================
    SEQ2RIBO module: predict riboseq profiles / TE / protein expression from mRNA sequence
    Upstream: https://github.com/Kingsford-Group/seq2ribo

    LICENSE: CMU Academic/Non-Commercial Research Use Only.
    Commercial use is prohibited. See https://github.com/Kingsford-Group/seq2ribo/blob/main/LICENSE

    NOTE: This model requires a CUDA-capable GPU. It will be auto-skipped
    under `--profile cpu`.
========================================================================================
*/

process SEQ2RIBO {
    tag "seq2ribo:${pred_task}:${cell_line}"
    label 'process_gpu'

    input:
    path input_fasta
    val pred_task
    val cell_line

    output:
    path "seq2ribo_output.json", emit: predictions

    script:
    def use_utr_flag = params.seq2ribo_use_utr ? '--use_utr' : ''
    """
    /opt/conda/envs/seq2ribo/bin/python /opt/seq2ribo/scripts/run_inference.py \\
        --task ${pred_task} \\
        --cell-line ${cell_line} \\
        --fasta ${input_fasta} \\
        ${use_utr_flag} \\
        --output seq2ribo_output.json
    """
}
