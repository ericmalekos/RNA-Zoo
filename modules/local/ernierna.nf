/*
========================================================================================
    ERNIERNA module: extract structure-aware RNA embeddings
    Upstream: https://github.com/Bruce-ywj/ERNIE-RNA
    Paper: Nature Communications 2025
    Input: FASTA of RNA sequences (max 1022 nt)
    Output: sequence_embeddings.npy (N x 768), labels.txt
========================================================================================
*/

process ERNIERNA {
    tag "ernierna"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "ernierna_out/sequence_embeddings.npy", emit: embeddings
    path "ernierna_out/labels.txt",              emit: labels
    path "ernierna_out/*_tokens.npy",            emit: token_embeddings, optional: true

    script:
    def per_token_flag = params.ernierna_per_token ? '--per-token' : ''
    """
    ernierna_predict.py \
        -i ${input_fasta} \
        -o ernierna_out \
        --max-len ${params.ernierna_max_len} \
        ${per_token_flag}
    """
}
