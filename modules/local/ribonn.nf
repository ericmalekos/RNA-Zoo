/*
========================================================================================
    RIBONN module: predict translation efficiency from mRNA sequence
    Upstream: https://github.com/Sanofi-Public/RiboNN
    Supports both bundled pretrained models and user-provided fine-tuned checkpoints.
========================================================================================
*/

process RIBONN {
    tag "ribonn"
    label 'process_medium'

    input:
    path tx_info
    path checkpoint, stageAs: 'finetuned.ckpt'

    output:
    path "ribonn_out/prediction_output.txt", emit: predictions

    script:
    def ckpt_flag = checkpoint.name != 'NO_CHECKPOINT' ? "--checkpoint ${checkpoint}" : ''
    def target_flag = params.ribonn_finetune_target && ckpt_flag ? "--target ${params.ribonn_finetune_target}" : ''
    """
    cp ${tx_info} /app/data/prediction_input1.txt
    cd /app && python3 /opt/bin/ribonn_predict.py \
        -i /app/data/prediction_input1.txt \
        -o "\$OLDPWD/ribonn_out" \
        --species ${params.ribonn_species ?: 'human'} \
        ${ckpt_flag} \
        ${target_flag}
    """
}
