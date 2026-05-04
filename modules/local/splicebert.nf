/*
========================================================================================
    SPLICEBERT module: extract embeddings from the SpliceBERT primary RNA sequence LM
    Upstream: https://github.com/biomed-AI/SpliceBERT (BSD-3-Clause)
    Paper: Chen et al., Briefings in Bioinformatics 2024 (10.1093/bib/bbae163)
    Weights: Zenodo 7995778, models.tar.gz, SpliceBERT.1024nt variant (CC-BY-4.0)
    Input: FASTA of RNA sequences (A/C/G/U/T, max 1024 nt each — 1026 minus CLS+SEP)
    Output: sequence_embeddings.npy (N x 512), labels.txt
========================================================================================
*/

process SPLICEBERT {
    tag "splicebert"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "splicebert_out/sequence_embeddings.npy", emit: embeddings
    path "splicebert_out/labels.txt",              emit: labels
    path "splicebert_out/*_tokens.npy",            emit: token_embeddings, optional: true

    script:
    def per_token_flag = params.splicebert_per_token ? '--per-token' : ''
    """
    splicebert_predict.py \
        -i ${input_fasta} \
        -o splicebert_out \
        --max-len ${params.splicebert_max_len} \
        --batch-size ${params.splicebert_batch_size} \
        ${per_token_flag}
    """
}
