/*
========================================================================================
    ORTHRUS_FINETUNE module: linear-probe MLP head on top of frozen Orthrus
    embeddings (512-d, mean_unpadded). Backbone is Mamba SSM, frozen.
    GPU-only — auto-skipped under -profile cpu (mamba-ssm needs CUDA at import).
    See modules/local/rnafm_finetune.nf for canonical pipeline.
========================================================================================
*/

process ORTHRUS_FINETUNE {
    tag "orthrus_finetune:${params.orthrus_finetune_label}"
    label 'process_high'

    input:
    path training_data

    output:
    path "orthrus_finetune_out/predictions.tsv", emit: predictions
    path "orthrus_finetune_out/best_head.pt",    emit: head_checkpoint
    path "orthrus_finetune_out/metrics.json",    emit: metrics

    script:
    """
    mkdir -p orthrus_finetune_out
    ${projectDir}/bin/tsv_to_fasta.py \\
        -i ${training_data} \\
        -o orthrus_finetune_input \\
        --label-col '${params.orthrus_finetune_label}'
    orthrus_predict.py \\
        -i orthrus_finetune_input.fa \\
        -o orthrus_embed_dir
    ${projectDir}/bin/finetune_head.py \\
        -e orthrus_embed_dir/sequence_embeddings.npy \\
        -l orthrus_finetune_input_labels.txt \\
        --names-fasta orthrus_finetune_input.fa \\
        -o orthrus_finetune_out \\
        --head-type ${params.orthrus_finetune_head_type} \\
        --task ${params.orthrus_finetune_task} \\
        --epochs ${params.orthrus_finetune_epochs} \\
        --lr ${params.orthrus_finetune_lr}
    """
}
