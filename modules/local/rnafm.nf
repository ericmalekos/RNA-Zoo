/*
========================================================================================
    RNAFM module: extract RNA foundation model embeddings from RNA sequences
    Upstream: https://github.com/ml4bio/RNA-FM
    Paper: Nature Machine Intelligence 2024
    Input: FASTA of RNA sequences (A/C/G/U, max 1024 nt each)
    Output: sequence_embeddings.npy (N x 640), labels.txt
========================================================================================
*/

process RNAFM {
    tag "rnafm"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "rnafm_out/sequence_embeddings.npy", emit: embeddings
    path "rnafm_out/labels.txt",              emit: labels
    path "rnafm_out/*_tokens.npy",            emit: token_embeddings, optional: true

    script:
    def per_token_flag = params.rnafm_per_token ? '--per-token' : ''
    """
    rnafm_predict.py \
        -i ${input_fasta} \
        -o rnafm_out \
        ${per_token_flag}
    """
}
