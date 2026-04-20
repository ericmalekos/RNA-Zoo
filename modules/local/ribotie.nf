/*
========================================================================================
    RIBOTIE module: detect translated ORFs from ribo-seq + sequence
    Upstream: https://github.com/TRISTAN-ORF/TRISTAN (v1.1.1, implements the RiboTIE
              paper model; wraps transcript_transformer v1.1.1).
    Pipeline steps:
      1) build HDF5 database from FASTA + GTF + BAM (--data)
      2) fine-tune the bundled pretrained human RiboTIE model on user's samples
      3) predict translated ORFs and emit per-sample GTF/CSV/NPY outputs

    NOTE: RiboTIE fine-tunes its model on the user's ribo-seq data before
    prediction. On CPU this is viable for small datasets (minutes) but slow
    for real-world ribo-seq experiments (hours+). Run with `-profile gpu` for
    realistic inputs.
========================================================================================
*/

process RIBOTIE {
    tag "ribotie"
    label 'process_high'

    input:
    path input_dir
    path config_yml

    output:
    path "ribotie_out/**.gtf",  emit: gtfs,        optional: true
    path "ribotie_out/**.csv",  emit: csvs,        optional: true
    path "ribotie_out/**.npy",  emit: npys,        optional: true
    path "ribotie_out/**.ckpt", emit: checkpoints, optional: true
    path "ribotie_out",         emit: out_dir

    script:
    def accelerator = params.device == 'cpu' ? 'cpu' : 'gpu'
    def max_epochs_flag = params.ribotie_max_epochs  != null ? "--max_epochs ${params.ribotie_max_epochs}" : ''
    def patience_flag   = params.ribotie_patience    != null ? "--patience ${params.ribotie_patience}"     : ''
    def checkpoint_override = params.ribotie_checkpoint
        ? "sed -i 's|^\\( *transfer_checkpoint *:.*\\)|  transfer_checkpoint : ${params.ribotie_checkpoint}|' config.yml"
        : "true  # no checkpoint override"
    """
    # RiboTIE expects paths in the YAML to be relative to the CWD it's run
    # from. Stage the user's input dir and config into this task's workdir
    # and run from here.
    mkdir -p ribotie_out/dbs ribotie_out/out

    # Copy config and rewrite paths to point into our staged input dir.
    # The YAML has paths like `data/SRR000001.bam` — we symlink the user's
    # input dir at `data/` and `gtf`/`fa` will resolve there. We also
    # override h5_path and out_prefix to point into ribotie_out/.
    ln -s "\$PWD/${input_dir}" data

    cp ${config_yml} config.yml
    # Remove `data : true` if present (that makes it skip inference).
    sed -i '/^data *: *true/d' config.yml
    # Override h5_path + out_prefix so outputs land in ribotie_out/
    sed -i 's|^h5_path *:.*|h5_path : ribotie_out/dbs/ribotie.h5|'  config.yml
    sed -i 's|^out_prefix *:.*|out_prefix : ribotie_out/out/ribotie|' config.yml
    # Optionally rewrite every transfer_checkpoint line to reuse a saved
    # fine-tuned checkpoint (from a previous ribotie run).
    ${checkpoint_override}

    ribotie config.yml \\
        --accelerator ${accelerator} \\
        --overwrite_data \\
        ${max_epochs_flag} ${patience_flag}
    """
}
