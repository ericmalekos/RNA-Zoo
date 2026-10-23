/*
========================================================================================
    SALUKI module: predict mRNA half-life from sequence
    Upstream: https://github.com/calico/basenji (Saluki model)
    Paper: Agarwal & Kelley, Genome Biology 2022
    Input: FASTA with lowercase=UTR, uppercase=CDS convention, and optionally a TSV of exon
           lengths per transcript (name, exon_lengths) to set the splice-junction channel
    Output: preds.npy (N x 1 x 50 ensemble members), names.txt and predictions.tsv, in
            Saluki's unitless consensus half-life score (first principal component of
            standardized log half-lives), not log2 half-life
========================================================================================
*/

process SALUKI {
    tag "saluki:${species}"
    label 'process_medium'

    input:
    path input_fasta
    val species
    path exons_tsv      // exon lengths per transcript, or NO_FILE

    output:
    path "saluki_out/preds.npy",       emit: predictions
    path "saluki_out/names.txt",       emit: names
    path "saluki_out/predictions.tsv", emit: table

    script:
    // species maps to data head index: 0=human, 1=mouse
    def data_head  = species == 'mouse' ? 1 : 0
    def exons_flag = exons_tsv.name == 'NO_FILE' ? '' : "--exons ${exons_tsv}"
    """
    saluki_predict.py \\
        -i ${input_fasta} \\
        -o saluki_out \\
        --data-head ${data_head} \\
        ${exons_flag}
    """
}
