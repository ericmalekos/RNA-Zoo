/*
========================================================================================
    CODONTRANSFORMER module: codon optimization for protein sequences
    Upstream: https://github.com/Adibvafa/CodonTransformer
    Paper: Nature Communications 2025
    Input: FASTA of amino acid sequences + target organism
    Output: FASTA of optimized DNA coding sequences
========================================================================================
*/

process CODONTRANSFORMER {
    tag "codontransformer:${organism.replaceAll(' ', '_')}"
    label 'process_medium'

    input:
    path input_fasta
    val organism

    output:
    path "optimized_codons.fa", emit: optimized_sequences

    script:
    // toString().toBoolean(): a command-line "false" arrives as a String, which Groovy treats as true
    def deterministic_flag = params.codontransformer_deterministic.toString().toBoolean() ? '--deterministic' : '--no-deterministic'
    """
    codon_transformer_predict.py \\
        -i ${input_fasta} \\
        -o optimized_codons.fa \\
        --organism "${organism}" \\
        ${deterministic_flag}
    """
}
