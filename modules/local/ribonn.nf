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
    def ckpt_flag   = params.ribonn_checkpoint ? "--checkpoint ${params.ribonn_checkpoint}" : ''
    def target_flag = params.ribonn_finetune_target && params.ribonn_checkpoint ? "--target ${params.ribonn_finetune_target}" : ''
    // The wrapper handles both pretrained and fine-tuned predictions and writes
    // only to user-supplied -o. We still `cd /app` so upstream predict.py can
    // resolve its relative `models/<species>/.../state_dict.pth` reads — but
    // nothing writes inside /app, so a read-only rootfs is fine.
    """
    INPUT_ABS=\$(readlink -f ${tx_info})
    OUT_ABS=\$PWD/ribonn_out
    mkdir -p "\$OUT_ABS"
    cd /app && python3 ${projectDir}/bin/ribonn_predict.py \
        -i "\$INPUT_ABS" \
        -o "\$OUT_ABS" \
        --species ${params.ribonn_species ?: 'human'} \
        ${ckpt_flag} \
        ${target_flag}
    """
}
