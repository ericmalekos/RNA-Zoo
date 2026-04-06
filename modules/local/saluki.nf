/*
========================================================================================
    SALUKI module: predict mRNA half-life from sequence
    Upstream: https://github.com/calico/basenji (Saluki model)
    Paper: Agarwal & Kelley, Genome Biology 2022
    Input: FASTA with lowercase=UTR, uppercase=CDS convention
    Output: preds.npy — NumPy array of log2(mRNA half-life) predictions
========================================================================================
*/

process SALUKI {
    tag "saluki:${species}"
    label 'process_medium'

    input:
    path input_fasta
    val species

    output:
    path "preds.npy", emit: predictions

    script:
    // species maps to data head index: 0=human, 1=mouse
    def data_head = species == 'mouse' ? 1 : 0
    """
    saluki_predict_fasta.py \\
        -d ${data_head} \\
        -o saluki_tmp \\
        /opt/saluki_models \\
        ${input_fasta}
    mv saluki_tmp/preds.npy preds.npy
    """
}
