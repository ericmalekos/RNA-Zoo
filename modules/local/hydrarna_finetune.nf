/*
========================================================================================
    HYDRARNA_FINETUNE module: linear-probe MLP head on top of frozen HydraRNA
    embeddings (1024-d). Backbone is hybrid Hydra-SSM + 2 MHA layers, frozen.
    GPU-only. Note: redistribution blocker on the upstream image (Google-Drive
    weights) — local-bake only until weights are mirrored to HF/Zenodo.
    See modules/local/rnafm_finetune.nf for canonical pipeline.
========================================================================================
*/

process HYDRARNA_FINETUNE {
    tag "hydrarna_finetune:${params.hydrarna_finetune_label}"
    label 'process_high'

    input:
    path training_data

    output:
    path "hydrarna_finetune_out/predictions.tsv", emit: predictions
    path "hydrarna_finetune_out/best_head.pt",    emit: head_checkpoint
    path "hydrarna_finetune_out/metrics.json",    emit: metrics

    script:
    """
    mkdir -p hydrarna_finetune_out
    ${projectDir}/bin/tsv_to_fasta.py \\
        -i ${training_data} \\
        -o hydrarna_finetune_input \\
        --label-col '${params.hydrarna_finetune_label}'
    hydrarna_predict.py \\
        -i hydrarna_finetune_input.fa \\
        -o hydrarna_embed_dir
    ${projectDir}/bin/finetune_head.py \\
        -e hydrarna_embed_dir/sequence_embeddings.npy \\
        -l hydrarna_finetune_input_labels.txt \\
        --names-fasta hydrarna_finetune_input.fa \\
        -o hydrarna_finetune_out \\
        --epochs ${params.hydrarna_finetune_epochs} \\
        --lr ${params.hydrarna_finetune_lr}
    """
}
