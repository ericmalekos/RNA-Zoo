/*
========================================================================================
    MRNABERT module: extract embeddings from the YYLY66/mRNABERT mRNA LM.
    Upstream: https://huggingface.co/YYLY66/mRNABERT
    Paper: Xiong et al., Nature Communications 2025 (s41467-025-65340-8)
    License: Apache-2.0 (code + weights, per HF YAML)
    Input: FASTA of mRNA sequences (DNA or RNA alphabet — wrapper auto-detects ORFs)
    Output: sequence_embeddings.npy (N x 768), labels.txt
========================================================================================
*/

process MRNABERT {
    tag "mrnabert"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "mrnabert_out/sequence_embeddings.npy", emit: embeddings
    path "mrnabert_out/labels.txt",              emit: labels
    path "mrnabert_out/*_tokens.npy",            emit: token_embeddings, optional: true

    script:
    def per_token_flag = params.mrnabert_per_token ? '--per-token' : ''
    """
    mrnabert_predict.py \\
        -i ${input_fasta} \\
        -o mrnabert_out \\
        --max-tokens ${params.mrnabert_max_tokens} \\
        ${per_token_flag}
    """
}
