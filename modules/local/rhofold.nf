/*
========================================================================================
    RHOFOLD module: predict RNA 3D structure from sequence
    Upstream: https://github.com/ml4bio/RhoFold
    Paper: Nature Methods 2024
    Input: FASTA of RNA sequences (max ~1022 nt)
    Output: PDB files (3D structure), CT files (secondary structure), NPZ (distograms)
========================================================================================
*/

process RHOFOLD {
    tag "rhofold"
    label 'process_high'

    input:
    path input_fasta

    output:
    path "rhofold_out/**/unrelaxed_model.pdb", emit: structures
    path "rhofold_out/**/ss.ct",               emit: secondary_structures
    path "rhofold_out/**/results.npz",         emit: distograms, optional: true
    path "rhofold_out/**/log.txt",             emit: logs,       optional: true
    path "rhofold_out",                        emit: out_dir

    script:
    """
    rhofold_predict.py \
        -i ${input_fasta} \
        -o rhofold_out \
        --relax-steps ${params.rhofold_relax_steps}
    """
}
