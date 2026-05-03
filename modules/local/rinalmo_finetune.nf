/*
========================================================================================
    RINALMO_FINETUNE module: linear-probe MLP head on top of frozen RiNALMo
    embeddings (1280-d). Largest backbone in the zoo (650M params); embedding
    extraction is slower than other foundation models. Backbone frozen.
    See modules/local/rnafm_finetune.nf for canonical pipeline.
========================================================================================
*/

process RINALMO_FINETUNE {
    tag "rinalmo_finetune:${params.rinalmo_finetune_label}"
    label 'process_medium'

    input:
    path training_data

    output:
    path "rinalmo_finetune_out/predictions.tsv", emit: predictions
    path "rinalmo_finetune_out/best_head.pt",    emit: head_checkpoint
    path "rinalmo_finetune_out/metrics.json",    emit: metrics

    script:
    """
    mkdir -p rinalmo_finetune_out
    ${projectDir}/bin/tsv_to_fasta.py \\
        -i ${training_data} \\
        -o rinalmo_finetune_input \\
        --label-col '${params.rinalmo_finetune_label}'
    rinalmo_predict.py \\
        -i rinalmo_finetune_input.fa \\
        -o rinalmo_embed_dir
    ${projectDir}/bin/finetune_head.py \\
        -e rinalmo_embed_dir/sequence_embeddings.npy \\
        -l rinalmo_finetune_input_labels.txt \\
        --names-fasta rinalmo_finetune_input.fa \\
        -o rinalmo_finetune_out \\
        --head-type ${params.rinalmo_finetune_head_type} \\
        --task ${params.rinalmo_finetune_task} \\
        --epochs ${params.rinalmo_finetune_epochs} \\
        --lr ${params.rinalmo_finetune_lr}
    """
}
