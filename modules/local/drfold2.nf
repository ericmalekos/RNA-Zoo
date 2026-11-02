/*
========================================================================================
    DRFOLD2 module: ab initio RNA 3D structure prediction.
    Upstream: https://github.com/leeyang/DRfold2
    Paper: Li et al., 2025 (preprint; "Ab initio RNA structure prediction with
           composite language model and denoised end-to-end learning")
    License: MIT (declared in upstream README; no LICENSE file on the repo).
             The weights and the bundled Arena (pylelab/Arena) carry no license
             statement; the image is redistributed with the authors' permission.
    Input: FASTA of RNA sequences. GPU-only.
    Output: <safe_label>.pdb per sequence
========================================================================================
*/

process DRFOLD2 {
    tag "drfold2"
    label 'process_high'

    input:
    path input_fasta

    output:
    path "drfold2_out/*.pdb", emit: structures

    script:
    // toString().toBoolean(): a command-line "--drfold2_cluster false" arrives as a String,
    // which Groovy treats as true
    def cluster_flag = params.drfold2_cluster.toString().toBoolean() ?
        "--cluster --cluster-timeout ${params.drfold2_cluster_timeout}" : ''
    def keep_flag    = params.drfold2_keep_intermediate.toString().toBoolean() ? '--keep-intermediate' : ''
    """
    drfold2_predict.py \\
        -i ${input_fasta} \\
        -o drfold2_out \\
        ${cluster_flag} ${keep_flag}
    """
}
