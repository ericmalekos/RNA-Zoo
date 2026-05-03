/*
========================================================================================
    RNAERNIE_FINETUNE module: linear-probe MLP head on top of frozen RNAErnie
    embeddings (768-d). See modules/local/rnafm_finetune.nf for canonical pipeline.
========================================================================================
*/

process RNAERNIE_FINETUNE {
    tag "rnaernie_finetune:${params.rnaernie_finetune_label}"
    label 'process_medium'

    input:
    path training_data

    output:
    path "rnaernie_finetune_out/predictions.tsv", emit: predictions
    path "rnaernie_finetune_out/best_head.pt",    emit: head_checkpoint
    path "rnaernie_finetune_out/metrics.json",    emit: metrics

    script:
    """
    mkdir -p rnaernie_finetune_out
    ${projectDir}/bin/tsv_to_fasta.py \\
        -i ${training_data} \\
        -o rnaernie_finetune_input \\
        --label-col '${params.rnaernie_finetune_label}'
    rnaernie_predict.py \\
        -i rnaernie_finetune_input.fa \\
        -o rnaernie_embed_dir
    ${projectDir}/bin/finetune_head.py \\
        -e rnaernie_embed_dir/sequence_embeddings.npy \\
        -l rnaernie_finetune_input_labels.txt \\
        --names-fasta rnaernie_finetune_input.fa \\
        -o rnaernie_finetune_out \\
        --epochs ${params.rnaernie_finetune_epochs} \\
        --lr ${params.rnaernie_finetune_lr}
    """
}
