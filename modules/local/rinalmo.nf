/*
========================================================================================
    RINALMO module: extract RNA embeddings from a 650M-parameter RNA language model
    Upstream: https://github.com/lbcb-sci/RiNALMo
    Paper: NeurIPS 2024
    Input: FASTA of RNA sequences
    Output: sequence_embeddings.npy (N x 1280), labels.txt
========================================================================================
*/

process RINALMO {
    tag "rinalmo"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "rinalmo_out/sequence_embeddings.npy", emit: embeddings
    path "rinalmo_out/labels.txt",              emit: labels
    path "rinalmo_out/*_tokens.npy",            emit: token_embeddings, optional: true

    script:
    def per_token_flag = params.rinalmo_per_token ? '--per-token' : ''
    """
    rinalmo_predict.py \
        -i ${input_fasta} \
        -o rinalmo_out \
        ${per_token_flag}
    """
}
