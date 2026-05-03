/*
========================================================================================
    MRNABERT_FINETUNE module: linear-probe MLP head on top of frozen mRNABERT
    embeddings (768-d). Backbone is frozen; ORF auto-detection happens in the
    predict wrapper. See modules/local/rnafm_finetune.nf for canonical pipeline.
========================================================================================
*/

process MRNABERT_FINETUNE {
    tag "mrnabert_finetune:${params.mrnabert_finetune_label}"
    label 'process_medium'

    input:
    path training_data

    output:
    path "mrnabert_finetune_out/predictions.tsv", emit: predictions
    path "mrnabert_finetune_out/best_head.pt",    emit: head_checkpoint
    path "mrnabert_finetune_out/metrics.json",    emit: metrics

    script:
    """
    mkdir -p mrnabert_finetune_out
    ${projectDir}/bin/tsv_to_fasta.py \\
        -i ${training_data} \\
        -o mrnabert_finetune_input \\
        --label-col '${params.mrnabert_finetune_label}'
    mrnabert_predict.py \\
        -i mrnabert_finetune_input.fa \\
        -o mrnabert_embed_dir
    ${projectDir}/bin/finetune_head.py \\
        -e mrnabert_embed_dir/sequence_embeddings.npy \\
        -l mrnabert_finetune_input_labels.txt \\
        --names-fasta mrnabert_finetune_input.fa \\
        -o mrnabert_finetune_out \\
        --head-type ${params.mrnabert_finetune_head_type} \\
        --task ${params.mrnabert_finetune_task} \\
        --epochs ${params.mrnabert_finetune_epochs} \\
        --lr ${params.mrnabert_finetune_lr}
    """
}
