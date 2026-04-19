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

    output:
    path "ribonn_out/prediction_output.txt", emit: predictions

    script:
    def use_wrapper = params.ribonn_checkpoint != null
    def ckpt_flag = params.ribonn_checkpoint ? "--checkpoint ${params.ribonn_checkpoint}" : ''
    def target_flag = params.ribonn_finetune_target && ckpt_flag ? "--target ${params.ribonn_finetune_target}" : ''
    if (use_wrapper)
    """
    cp ${tx_info} /app/data/prediction_input1.txt
    cd /app && python3 /opt/bin/ribonn_predict.py \
        -i /app/data/prediction_input1.txt \
        -o "\$OLDPWD/ribonn_out" \
        --species ${params.ribonn_species ?: 'human'} \
        ${ckpt_flag} \
        ${target_flag}
    """
    else
    """
    cp ${tx_info} /app/data/prediction_input1.txt
    cd /app && python3 -m src.main --predict ${params.ribonn_species ?: 'human'}
    mkdir -p "\$OLDPWD/ribonn_out"
    cp /app/results/${params.ribonn_species ?: 'human'}/prediction_output.txt "\$OLDPWD/ribonn_out/prediction_output.txt"
    """
}
