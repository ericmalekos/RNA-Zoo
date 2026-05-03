/*
========================================================================================
    PLANTRNAFM_FINETUNE module: linear-probe MLP head on top of frozen
    PlantRNA-FM embeddings (480-d). Plant-domain backbone is frozen.
    See modules/local/rnafm_finetune.nf for canonical pipeline.
========================================================================================
*/

process PLANTRNAFM_FINETUNE {
    tag "plantrnafm_finetune:${params.plantrnafm_finetune_label}"
    label 'process_medium'

    input:
    path training_data

    output:
    path "plantrnafm_finetune_out/predictions.tsv", emit: predictions
    path "plantrnafm_finetune_out/best_head.pt",    emit: head_checkpoint
    path "plantrnafm_finetune_out/metrics.json",    emit: metrics

    script:
    """
    mkdir -p plantrnafm_finetune_out
    ${projectDir}/bin/tsv_to_fasta.py \\
        -i ${training_data} \\
        -o plantrnafm_finetune_input \\
        --label-col '${params.plantrnafm_finetune_label}'
    plantrnafm_predict.py \\
        -i plantrnafm_finetune_input.fa \\
        -o plantrnafm_embed_dir
    ${projectDir}/bin/finetune_head.py \\
        -e plantrnafm_embed_dir/sequence_embeddings.npy \\
        -l plantrnafm_finetune_input_labels.txt \\
        --names-fasta plantrnafm_finetune_input.fa \\
        -o plantrnafm_finetune_out \\
        --head-type ${params.plantrnafm_finetune_head_type} \\
        --task ${params.plantrnafm_finetune_task} \\
        --epochs ${params.plantrnafm_finetune_epochs} \\
        --lr ${params.plantrnafm_finetune_lr}
    """
}
