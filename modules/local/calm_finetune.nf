/*
========================================================================================
    CALM_FINETUNE module: linear-probe MLP head on top of frozen CaLM
    codon-level embeddings (768-d). Backbone is frozen.

    Note: CaLM tokenizes at the codon level, not nucleotide. The predict
    wrapper auto-trims non-codon-aligned sequences to the nearest multiple
    of 3 with a warning — fine for smoke but real fine-tuning data should
    be codon-aligned CDS sequences.

    See modules/local/rnafm_finetune.nf for canonical pipeline.
========================================================================================
*/

process CALM_FINETUNE {
    tag "calm_finetune:${params.calm_finetune_label}"
    label 'process_medium'

    input:
    path training_data

    output:
    path "calm_finetune_out/predictions.tsv", emit: predictions
    path "calm_finetune_out/best_head.pt",    emit: head_checkpoint
    path "calm_finetune_out/metrics.json",    emit: metrics

    script:
    """
    mkdir -p calm_finetune_out
    ${projectDir}/bin/tsv_to_fasta.py \\
        -i ${training_data} \\
        -o calm_finetune_input \\
        --label-col '${params.calm_finetune_label}'
    calm_predict.py \\
        -i calm_finetune_input.fa \\
        -o calm_embed_dir
    ${projectDir}/bin/finetune_head.py \\
        -e calm_embed_dir/sequence_embeddings.npy \\
        -l calm_finetune_input_labels.txt \\
        --names-fasta calm_finetune_input.fa \\
        -o calm_finetune_out \\
        --epochs ${params.calm_finetune_epochs} \\
        --lr ${params.calm_finetune_lr}
    """
}
