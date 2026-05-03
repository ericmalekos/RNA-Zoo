/*
========================================================================================
    ERNIERNA_FINETUNE module: linear-probe MLP head on top of frozen ERNIE-RNA
    embeddings. Backbone (12L 768-d, structure-aware attention) is frozen.

    See modules/local/rnafm_finetune.nf for the canonical 3-step pipeline.
========================================================================================
*/

process ERNIERNA_FINETUNE {
    tag "ernierna_finetune:${params.ernierna_finetune_label}"
    label 'process_medium'

    input:
    path training_data

    output:
    path "ernierna_finetune_out/predictions.tsv", emit: predictions
    path "ernierna_finetune_out/best_head.pt",    emit: head_checkpoint
    path "ernierna_finetune_out/metrics.json",    emit: metrics

    script:
    """
    mkdir -p ernierna_finetune_out
    ${projectDir}/bin/tsv_to_fasta.py \\
        -i ${training_data} \\
        -o ernierna_finetune_input \\
        --label-col '${params.ernierna_finetune_label}'
    ernierna_predict.py \\
        -i ernierna_finetune_input.fa \\
        -o ernierna_embed_dir
    ${projectDir}/bin/finetune_head.py \\
        -e ernierna_embed_dir/sequence_embeddings.npy \\
        -l ernierna_finetune_input_labels.txt \\
        --names-fasta ernierna_finetune_input.fa \\
        -o ernierna_finetune_out \\
        --head-type ${params.ernierna_finetune_head_type} \\
        --task ${params.ernierna_finetune_task} \\
        --epochs ${params.ernierna_finetune_epochs} \\
        --lr ${params.ernierna_finetune_lr}
    """
}
