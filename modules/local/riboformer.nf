/*
========================================================================================
    RIBOFORMER module: predict codon-level ribosome densities from ribo-seq + sequence
    Upstream: https://github.com/lingxusb/Riboformer
    Two-step pipeline:
      1) data_processing.py — WIG/FASTA/GFF3 → xc.txt/yc.txt/zc.txt tensors
      2) transfer.py        — tensors → model_prediction.txt
========================================================================================
*/

process RIBOFORMER {
    tag "riboformer:${model_name}"
    label 'process_medium'

    input:
    path input_dir
    val model_name
    val reference_wig
    val target_wig

    output:
    path "model_prediction.txt", emit: predictions
    path "pause_indices.txt",    emit: pause_indices, optional: true

    script:
    """
    # Riboformer's scripts expect to be run from /opt/Riboformer/Riboformer/
    # and read/write files under /opt/Riboformer/datasets/<name>/.
    # Stage the user's input dir into the container's datasets/ location,
    # then run both pipeline steps.
    NF_WORKDIR="\$PWD"
    DATASET_NAME="nf_input"
    DATASET_DIR="/opt/Riboformer/datasets/\$DATASET_NAME"
    mkdir -p "\$DATASET_DIR"
    cp ${input_dir}/* "\$DATASET_DIR/"

    # Step 1: convert WIG + FASTA + GFF3 into xc/yc/zc tensors
    ( cd /opt/Riboformer/Riboformer && python data_processing.py \\
        -d "\$DATASET_NAME" \\
        -r "${reference_wig}" \\
        -t "${target_wig}" \\
        -p ${params.riboformer_psite} \\
        -w ${params.riboformer_wsize} \\
        -th ${params.riboformer_threshold} )

    # Step 2: run the model on the processed tensors
    ( cd /opt/Riboformer/Riboformer && python transfer.py -i "\$DATASET_NAME" -m "${model_name}" )

    # Stage outputs back to task workdir for Nextflow publishing
    cd "\$NF_WORKDIR"
    cp "\$DATASET_DIR/model_prediction.txt" model_prediction.txt
    if [ -f "\$DATASET_DIR/pause_indices.txt" ]; then
        cp "\$DATASET_DIR/pause_indices.txt" pause_indices.txt
    fi
    """
}
