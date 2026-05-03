/*
========================================================================================
    HYDRARNA module: extract embeddings from the GuipengLi/HydraRNA full-length RNA LM.
    Upstream: https://github.com/GuipengLi/HydraRNA
    Paper: Li et al., Genome Biology 2025 (s13059-025-03853-7)
    License: MIT (upstream LICENSE; copyright header has a typo "GPL" but body is MIT)
    Input: FASTA of RNA sequences (max 10K nt; longer is auto-chunked)
    Output: sequence_embeddings.npy (N x 1024), labels.txt
    Runtime: GPU-only — Mamba SSM + flash-attention require CUDA at import.
========================================================================================
*/

process HYDRARNA {
    tag "hydrarna"
    label 'process_high'

    input:
    path input_fasta

    output:
    path "hydrarna_out/sequence_embeddings.npy", emit: embeddings
    path "hydrarna_out/labels.txt",              emit: labels
    path "hydrarna_out/*_tokens.npy",            emit: token_embeddings, optional: true

    script:
    def per_token_flag = params.hydrarna_per_token ? '--per-token' : ''
    def no_half_flag   = params.hydrarna_no_half  ? '--no-half'  : ''
    """
    hydrarna_predict.py \\
        -i ${input_fasta} \\
        -o hydrarna_out \\
        ${no_half_flag} \\
        ${per_token_flag}
    """
}
