/*
========================================================================================
    CALM module: extract codon-level embeddings from CaLM (Codon adaptation LM).
    Upstream: https://github.com/oxpig/CaLM
    Paper: Outeiral & Deane, Nature Machine Intelligence 2024 (s42256-024-00791-0)
    License: BSD-3-Clause (code), BSD-3-Clause (weights, OPIG redistribution OK)
    Input: FASTA of RNA / CDS sequences (max 1024 codons each)
    Output: sequence_embeddings.npy (N x 768), labels.txt
========================================================================================
*/

process CALM {
    tag "calm"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "calm_out/sequence_embeddings.npy", emit: embeddings
    path "calm_out/labels.txt",              emit: labels
    path "calm_out/*_tokens.npy",            emit: token_embeddings, optional: true

    script:
    def per_token_flag = params.calm_per_token ? '--per-token' : ''
    """
    calm_predict.py \\
        -i ${input_fasta} \\
        -o calm_out \\
        ${per_token_flag}
    """
}
