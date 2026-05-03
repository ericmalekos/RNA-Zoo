// Generic head trainer that bypasses the per-model predict step.
// Aliased once per foundation model in workflows/rnazoo.nf so each invocation
// gets its own per-model publishDir while sharing the same image
// (rnazoo-finetune-head, configured per-alias in conf/modules.config).
//
// The meta map carries:
//   name      — model short name (used for output dirs / tags)
//   label_col — column name in the TSV
//   epochs    — max epochs for torch heads (xgboost ignores)
//   lr        — Adam lr (torch) or xgboost learning_rate
//   head_type — linear | mlp | xgboost
//   task      — auto | regression | classification
process FINETUNE_HEAD_ONLY {
    tag "${meta.name}_finetune_from_emb:${meta.label_col}:${meta.head_type}"
    label 'process_medium'

    input:
    tuple val(meta), path(input_tsv), path(embeddings)

    output:
    path "${meta.name}_finetune_out/predictions.tsv",     emit: predictions
    path "${meta.name}_finetune_out/metrics.json",        emit: metrics
    path "${meta.name}_finetune_out/best_head.{pt,ubj}",  emit: head_checkpoint
    path "${meta.name}_finetune_out/best_head_config.json", optional: true, emit: head_config

    script:
    """
    mkdir -p ${meta.name}_finetune_out
    ${projectDir}/bin/tsv_to_fasta.py \\
        -i ${input_tsv} \\
        -o ${meta.name}_finetune_input \\
        --label-col '${meta.label_col}' \\
        --no-fasta
    ${projectDir}/bin/finetune_head.py \\
        -e ${embeddings} \\
        -l ${meta.name}_finetune_input_labels.txt \\
        --names ${meta.name}_finetune_input_names.txt \\
        -o ${meta.name}_finetune_out \\
        --head-type ${meta.head_type} \\
        --task ${meta.task} \\
        --epochs ${meta.epochs} \\
        --lr ${meta.lr}
    """
}
