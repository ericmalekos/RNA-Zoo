/*
========================================================================================
    PLANTRNAFM module: extract embeddings from the PlantRNA-FM plant-only RNA LM
    Upstream: https://huggingface.co/yangheng/PlantRNA-FM
    Paper: Yu, Yang et al., Nature Machine Intelligence 2024 (s42256-024-00946-z)
    License: MIT (per HF YAML)
    Input: FASTA of RNA sequences (A/C/G/U, max 1024 nt each — 1026 minus CLS+EOS)
    Output: sequence_embeddings.npy (N x 480), labels.txt
========================================================================================
*/

process PLANTRNAFM {
    tag "plantrnafm"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "plantrnafm_out/sequence_embeddings.npy", emit: embeddings
    path "plantrnafm_out/labels.txt",              emit: labels
    path "plantrnafm_out/*_tokens.npy",            emit: token_embeddings, optional: true

    script:
    def per_token_flag = params.plantrnafm_per_token ? '--per-token' : ''
    """
    plantrnafm_predict.py \
        -i ${input_fasta} \
        -o plantrnafm_out \
        ${per_token_flag}
    """
}
