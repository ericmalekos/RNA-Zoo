/*
========================================================================================
    RIBONN_FINETUNE module: fine-tune RiboNN on user TE data via transfer learning
    Uses pretrained human multi-task model as initialization, then fine-tunes
    on a user-provided target column (e.g., a new cell type or condition).
    Input: tab-separated file (tx_id, utr5_sequence, cds_sequence, utr3_sequence, <target>)
    Output: fine-tuned model checkpoints + cross-validated predictions
========================================================================================
*/

process RIBONN_FINETUNE {
    tag "ribonn_finetune:${params.ribonn_finetune_target}"
    label 'process_high'

    input:
    path training_data

    output:
    path "ribonn_finetune_out/predictions.tsv", emit: predictions
    path "ribonn_finetune_out/fold*",           emit: checkpoints, optional: true

    script:
    """
    cp ${training_data} /app/data/user_training_data.txt
    cd /app && python3 /opt/bin/ribonn_finetune.py \
        -i /app/data/user_training_data.txt \
        -o "\$OLDPWD/ribonn_finetune_out" \
        --target "${params.ribonn_finetune_target}" \
        --phase1-epochs ${params.ribonn_finetune_phase1_epochs} \
        --phase2-epochs ${params.ribonn_finetune_phase2_epochs} \
        --patience ${params.ribonn_finetune_patience} \
        --folds ${params.ribonn_finetune_folds}
    """
}
