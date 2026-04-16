/*
========================================================================================
    RNAFORMER module: predict RNA secondary structure (base-pair matrix) from sequence
    Upstream: https://github.com/automl/RNAformer
    Paper: ICLR 2024
    Input: FASTA of RNA sequences (max ~500 nt)
    Output: structures.txt (FASTA-like: header, sequence, dot-bracket)
========================================================================================
*/

process RNAFORMER {
    tag "rnaformer"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "rnaformer_out/structures.txt", emit: structures
    path "rnaformer_out/*_bpmat.npy",    emit: matrices, optional: true

    script:
    def matrix_flag = params.rnaformer_save_matrix ? '--save-matrix' : ''
    """
    rnaformer_predict.py \
        -i ${input_fasta} \
        -o rnaformer_out \
        --cycling ${params.rnaformer_cycling} \
        ${matrix_flag}
    """
}
