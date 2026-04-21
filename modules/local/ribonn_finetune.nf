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
    // `cd /app` lets upstream resolve relative `models/human/.../state_dict.pth`
    // reads; the wrapper writes only to user-supplied -o, so /app stays clean.
    """
    INPUT_ABS=\$(readlink -f ${training_data})
    OUT_ABS=\$PWD/ribonn_finetune_out
    mkdir -p "\$OUT_ABS"
    cd /app && python3 ${projectDir}/bin/ribonn_finetune.py \
        -i "\$INPUT_ABS" \
        -o "\$OUT_ABS" \
        --target "${params.ribonn_finetune_target}" \
        --phase1-epochs ${params.ribonn_finetune_phase1_epochs} \
        --phase2-epochs ${params.ribonn_finetune_phase2_epochs} \
        --patience ${params.ribonn_finetune_patience} \
        --folds ${params.ribonn_finetune_folds}
    """
}
