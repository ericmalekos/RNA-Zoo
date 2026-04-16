/*
========================================================================================
    UTRLM_FINETUNE module: fine-tune UTR-LM on user expression data
    Input: CSV/TSV with columns: name, utr, <label_column>
    Output: fine-tuned model checkpoint + predictions
========================================================================================
*/

process UTRLM_FINETUNE {
    tag "utrlm_finetune:${params.utrlm_finetune_task}"
    label 'process_high'

    input:
    path training_data

    output:
    path "utrlm_finetune_out/predictions.tsv", emit: predictions
    path "utrlm_finetune_out/best_model.pt",   emit: model

    script:
    def pretrained_flag = params.utrlm_finetune_pretrained ? "--pretrained ${params.utrlm_finetune_pretrained}" : ''
    """
    utrlm_finetune.py \
        -i ${training_data} \
        -o utrlm_finetune_out \
        --label "${params.utrlm_finetune_label}" \
        --task ${params.utrlm_finetune_task} \
        --epochs ${params.utrlm_finetune_epochs} \
        --patience ${params.utrlm_finetune_patience} \
        --lr ${params.utrlm_finetune_lr} \
        --model-dir /opt/utrlm/Model \
        ${pretrained_flag}
    """
}
