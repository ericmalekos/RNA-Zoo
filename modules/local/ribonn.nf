/*
========================================================================================
    RIBONN module: predict translation efficiency from mRNA sequence
    Upstream: https://github.com/Sanofi-Public/RiboNN
========================================================================================
*/

process RIBONN {
    tag "ribonn"
    label 'process_medium'

    input:
    path tx_info

    output:
    path "prediction_output.txt", emit: predictions

    script:
    """
    # The RiboNN image has its code, data/, models/, at /app.
    # Nextflow runs us from a task workdir, so we stage inputs to /app/data/,
    # cd to /app to run, then copy outputs back to the task workdir.
    cp ${tx_info} /app/data/prediction_input1.txt
    cd /app && python3 -m src.main --predict human
    cp /app/results/human/prediction_output.txt "\$OLDPWD/prediction_output.txt"
    """
}
