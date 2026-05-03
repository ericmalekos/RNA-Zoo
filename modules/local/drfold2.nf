/*
========================================================================================
    DRFOLD2 module: ab initio RNA 3D structure prediction.
    Upstream: https://github.com/leeyang/DRfold2
    Paper: Li et al., 2025 (preprint; "Ab initio RNA structure prediction with
           composite language model and denoised end-to-end learning")
    License: MIT (declared in upstream README; no LICENSE file on the repo).
             Bundled Arena binary has NO LICENSE on its upstream repo (pylelab/Arena)
             — flag in docs before pushing to ghcr.
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
    def cluster_flag = params.drfold2_cluster ? '--cluster' : ''
    def keep_flag    = params.drfold2_keep_intermediate ? '--keep-intermediate' : ''
    """
    drfold2_predict.py \\
        -i ${input_fasta} \\
        -o drfold2_out \\
        ${cluster_flag} ${keep_flag}
    """
}
