/*
========================================================================================
    ORTHRUS module: Mamba-based mature mRNA foundation model embeddings
    Upstream: https://github.com/bowang-lab/Orthrus
    Paper: Nature Methods 2026
    Input: FASTA of complete mature mRNA sequences (A/C/G/U or A/C/G/T)
    Output: sequence_embeddings.npy (N x 256), labels.txt

    NOTE: Orthrus uses Mamba's CUDA selective-scan kernel and requires a
    GPU. The workflow auto-skips this process under `--profile cpu`.
========================================================================================
*/

process ORTHRUS {
    tag "orthrus"
    label 'process_gpu'

    input:
    path input_fasta

    output:
    path "orthrus_out/sequence_embeddings.npy", emit: embeddings
    path "orthrus_out/labels.txt",              emit: labels
    path "orthrus_out/*_tokens.npy",            emit: token_embeddings, optional: true

    script:
    def per_token_flag = params.orthrus_per_token ? '--per-token' : ''
    """
    orthrus_predict.py \
        -i ${input_fasta} \
        -o orthrus_out \
        --variant ${params.orthrus_variant} \
        ${per_token_flag}
    """
}
