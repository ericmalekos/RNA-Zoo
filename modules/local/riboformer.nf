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
    path "model_prediction.txt",        emit: predictions
    path "pause_indices.txt",           emit: pause_indices, optional: true
    path "ribosome_density_plot.png",   emit: plot, optional: true

    script:
    def use_bundled = params.riboformer_bundled_dataset != null
    def src_dataset = use_bundled
        ? "/opt/Riboformer/datasets/${params.riboformer_bundled_dataset}"
        : "${input_dir}"
    """
    # Riboformer's scripts compute their base dir as dirname(cwd) and both read
    # AND write under <base>/datasets/<name>/. Running them against the in-image
    # /opt/Riboformer tree fails on read-only-rootfs runtimes (Singularity CE 3.8
    # underlay mode). Instead we stage everything into the Nextflow work dir.
    NF_WORKDIR="\$PWD"
    DATASET_DIR="\$NF_WORKDIR/datasets/nf_input"
    RUN_DIR="\$NF_WORKDIR/run"
    mkdir -p "\$DATASET_DIR" "\$RUN_DIR"

    cp -rL ${src_dataset}/* "\$DATASET_DIR/"

    # Symlinks so scripts find the in-image models + codon table without writes.
    ln -sfn /opt/Riboformer/models "\$NF_WORKDIR/models"
    ln -sfn /opt/Riboformer/Riboformer/codon_table.json "\$RUN_DIR/codon_table.json"

    # cd into a subdir so os.path.dirname(os.getcwd()) resolves to \$NF_WORKDIR.
    cd "\$RUN_DIR"

    python /opt/Riboformer/Riboformer/data_processing.py \\
        -d nf_input \\
        -r "${reference_wig}" \\
        -t "${target_wig}" \\
        -p ${params.riboformer_psite} \\
        -w ${params.riboformer_wsize} \\
        -th ${params.riboformer_threshold}

    python /opt/Riboformer/Riboformer/transfer.py -i nf_input -m "${model_name}"

    cd "\$NF_WORKDIR"
    cp "\$DATASET_DIR/model_prediction.txt" model_prediction.txt
    if [ -f "\$DATASET_DIR/pause_indices.txt" ]; then
        cp "\$DATASET_DIR/pause_indices.txt" pause_indices.txt
    fi

    if [ "${params.riboformer_plot}" = "true" ]; then
        python -c "
import sys
sys.path.insert(0, '/opt/bin')
from rnazoo_plots import plot_ribosome_density
import numpy as np
d = np.loadtxt('model_prediction.txt')
plot_ribosome_density(d, '${model_name}', 'ribosome_density_plot.png')
" || true
    fi
    """
}
