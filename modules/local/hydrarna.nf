/*
========================================================================================
    HYDRARNA module: hybrid Hydra-SSM + MHA full-length RNA language model embeddings
    Upstream: https://github.com/GuipengLi/HydraRNA
    Paper: Genome Biology 2025 (doi:10.1186/s13059-025-03853-7)
    Input: FASTA of RNA sequences (A/C/G/U or A/C/G/T; ≤10K nt optimal)
    Output: sequence_embeddings.npy (N x 1024), labels.txt

    NOTE: HydraRNA uses Mamba's CUDA selective-scan kernel and requires a
    GPU. The workflow auto-skips this process under `--profile cpu`.
========================================================================================
*/

process HYDRARNA {
    tag "hydrarna"
    label 'process_gpu'

    input:
    path input_fasta

    output:
    path "hydrarna_out/sequence_embeddings.npy", emit: embeddings
    path "hydrarna_out/labels.txt",              emit: labels
    path "hydrarna_out/*_tokens.npy",            emit: token_embeddings, optional: true

    script:
    def per_token_flag = params.hydrarna_per_token ? '--per-token' : ''
    """
    hydrarna_predict.py \\
        -i ${input_fasta} \\
        -o hydrarna_out \\
        --max-len ${params.hydrarna_max_len} \\
        ${per_token_flag}
    """
}
