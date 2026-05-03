/*
========================================================================================
    RNAFM_FINETUNE module: linear-probe MLP head on top of frozen RNA-FM embeddings.

    Pipeline (3 steps inside one container):
      TSV/CSV (name, sequence, label)
        → tsv_to_fasta.py → FASTA + labels.txt
        → rnafm_predict.py (baked at /opt/bin) → sequence_embeddings.npy
        → finetune_head.py → best_head.pt + predictions.tsv + metrics.json

    Backbone (RNA-FM 12L 640-d) is frozen; only the MLP head trains.
    For full backbone fine-tuning, see UTR-LM's pattern (different scope).
========================================================================================
*/

process RNAFM_FINETUNE {
    tag "rnafm_finetune:${params.rnafm_finetune_label}"
    label 'process_medium'

    input:
    path training_data

    output:
    path "rnafm_finetune_out/predictions.tsv", emit: predictions
    path "rnafm_finetune_out/best_head.pt",    emit: head_checkpoint
    path "rnafm_finetune_out/metrics.json",    emit: metrics

    script:
    """
    mkdir -p rnafm_finetune_out
    ${projectDir}/bin/tsv_to_fasta.py \\
        -i ${training_data} \\
        -o rnafm_finetune_input \\
        --label-col '${params.rnafm_finetune_label}'
    rnafm_predict.py \\
        -i rnafm_finetune_input.fa \\
        -o rnafm_embed_dir
    ${projectDir}/bin/finetune_head.py \\
        -e rnafm_embed_dir/sequence_embeddings.npy \\
        -l rnafm_finetune_input_labels.txt \\
        --names-fasta rnafm_finetune_input.fa \\
        -o rnafm_finetune_out \\
        --epochs ${params.rnafm_finetune_epochs} \\
        --lr ${params.rnafm_finetune_lr}
    """
}
