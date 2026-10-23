/*
========================================================================================
    SPOTRNA module: predict RNA secondary structure including pseudoknots
    Upstream: https://github.com/jaswindersingh2/SPOT-RNA
    Paper: Nature Communications 2019
    Input: FASTA of RNA sequences
    Output: dot-bracket structures, bpseq, ct, probability matrices
========================================================================================
*/

process SPOTRNA {
    tag "spotrna"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "spotrna_out/structures.txt", emit: structures
    path "spotrna_out/*.bpseq",        emit: bpseq,  optional: true
    path "spotrna_out/*.ct",           emit: ct,     optional: true
    path "spotrna_out/*.prob",         emit: prob,   optional: true
    path "spotrna_out/*_contact.png",  emit: plots,  optional: true

    script:
    // toString().toBoolean(): a command-line "--spotrna_plot false" arrives as a String,
    // which Groovy treats as true
    def plot_flag = params.spotrna_plot.toString().toBoolean() ? '--plot' : ''
    def gpu_index = params.device == 'gpu' ? 0 : -1
    """
    spotrna_predict.py \
        -i ${input_fasta} \
        -o spotrna_out \
        --gpu ${gpu_index} \
        --cpu ${task.cpus} \
        ${plot_flag}
    """
}
