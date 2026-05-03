/*
========================================================================================
    RNAERNIE module: extract embeddings from the RNAErnie ERNIE-framework RNA LM
    Upstream (original PaddlePaddle): https://github.com/CatIIIIIIII/RNAErnie (MIT)
    Paper: Wang et al., Nature Machine Intelligence 2024 (s42256-024-00836-4)
    HF port (used here): LLM-EDA/RNAErnie (Apache-2.0) — official PyTorch port
    Input: FASTA of RNA sequences (A/C/G/U, max 2046 nt each — 2048 minus CLS+SEP)
    Output: sequence_embeddings.npy (N x 768), labels.txt
========================================================================================
*/

process RNAERNIE {
    tag "rnaernie"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "rnaernie_out/sequence_embeddings.npy", emit: embeddings
    path "rnaernie_out/labels.txt",              emit: labels
    path "rnaernie_out/*_tokens.npy",            emit: token_embeddings, optional: true

    script:
    def per_token_flag = params.rnaernie_per_token ? '--per-token' : ''
    """
    rnaernie_predict.py \
        -i ${input_fasta} \
        -o rnaernie_out \
        --max-len ${params.rnaernie_max_len} \
        --batch-size ${params.rnaernie_batch_size} \
        ${per_token_flag}
    """
}
