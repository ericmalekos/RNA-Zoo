/*
========================================================================================
    RNAZOO workflow: dispatch input to each enabled model module.
    Models are opt-in — only those with a non-null _input parameter will run.
========================================================================================
*/

include { RIBONN           } from '../modules/local/ribonn'
include { RIBONN_FINETUNE  } from '../modules/local/ribonn_finetune'
include { RIBOFORMER       } from '../modules/local/riboformer'
include { RIBOTIE          } from '../modules/local/ribotie'
include { SEQ2RIBO         } from '../modules/local/seq2ribo'
include { SALUKI           } from '../modules/local/saluki'
include { TRANSLATIONAI    } from '../modules/local/translationai'
include { CODONTRANSFORMER } from '../modules/local/codontransformer'
include { RNAFM            } from '../modules/local/rnafm'
include { RNAFM_FINETUNE   } from '../modules/local/rnafm_finetune'
include { RINALMO          } from '../modules/local/rinalmo'
include { RINALMO_FINETUNE } from '../modules/local/rinalmo_finetune'
include { ERNIERNA         } from '../modules/local/ernierna'
include { ERNIERNA_FINETUNE } from '../modules/local/ernierna_finetune'
include { ORTHRUS          } from '../modules/local/orthrus'
include { ORTHRUS_FINETUNE } from '../modules/local/orthrus_finetune'
include { RNAERNIE         } from '../modules/local/rnaernie'
include { RNAERNIE_FINETUNE } from '../modules/local/rnaernie_finetune'
include { PLANTRNAFM       } from '../modules/local/plantrnafm'
include { PLANTRNAFM_FINETUNE } from '../modules/local/plantrnafm_finetune'
include { SPLICEBERT       } from '../modules/local/splicebert'
include { SPLICEAI         } from '../modules/local/spliceai'
include { PANGOLIN         } from '../modules/local/pangolin'
include { CALM             } from '../modules/local/calm'
include { CALM_FINETUNE    } from '../modules/local/calm_finetune'
include { MRNABERT         } from '../modules/local/mrnabert'
include { MRNABERT_FINETUNE } from '../modules/local/mrnabert_finetune'
include { HYDRARNA         } from '../modules/local/hydrarna'
include { HYDRARNA_FINETUNE } from '../modules/local/hydrarna_finetune'
include { RNAFORMER        } from '../modules/local/rnaformer'
include { RHOFOLD          } from '../modules/local/rhofold'
include { SPOTRNA          } from '../modules/local/spotrna'
include { DRFOLD2          } from '../modules/local/drfold2'
include { MULTIRM          } from '../modules/local/multirm'
include { UTRLM            } from '../modules/local/utrlm'
include { UTRLM_FINETUNE   } from '../modules/local/utrlm_finetune'

// Precomputed-embeddings short-circuit for foundation-model fine-tunes.
// One generic FINETUNE_HEAD_ONLY process is aliased per model so each invocation
// can run in the corresponding model's image (configured per-alias in
// conf/modules.config).
include { FINETUNE_HEAD_ONLY as RNAFM_FINETUNE_FROM_EMB      } from '../modules/local/finetune_head_only'
include { FINETUNE_HEAD_ONLY as RINALMO_FINETUNE_FROM_EMB    } from '../modules/local/finetune_head_only'
include { FINETUNE_HEAD_ONLY as ERNIERNA_FINETUNE_FROM_EMB   } from '../modules/local/finetune_head_only'
include { FINETUNE_HEAD_ONLY as ORTHRUS_FINETUNE_FROM_EMB    } from '../modules/local/finetune_head_only'
include { FINETUNE_HEAD_ONLY as RNAERNIE_FINETUNE_FROM_EMB   } from '../modules/local/finetune_head_only'
include { FINETUNE_HEAD_ONLY as PLANTRNAFM_FINETUNE_FROM_EMB } from '../modules/local/finetune_head_only'
include { FINETUNE_HEAD_ONLY as CALM_FINETUNE_FROM_EMB       } from '../modules/local/finetune_head_only'
include { FINETUNE_HEAD_ONLY as MRNABERT_FINETUNE_FROM_EMB   } from '../modules/local/finetune_head_only'
include { FINETUNE_HEAD_ONLY as HYDRARNA_FINETUNE_FROM_EMB   } from '../modules/local/finetune_head_only'

workflow RNAZOO {
    main:

    // ----- Translation -----

    if (params.ribonn_input) {
        RIBONN(Channel.fromPath(params.ribonn_input, checkIfExists: true))
    }

    if (params.ribonn_finetune_input) {
        if (!params.ribonn_finetune_target) {
            error "ribonn_finetune_target is required when ribonn_finetune_input is set"
        }
        RIBONN_FINETUNE(Channel.fromPath(params.ribonn_finetune_input, checkIfExists: true))
    }

    if (params.riboformer_input || params.riboformer_bundled_dataset) {
        if (!params.riboformer_reference_wig || !params.riboformer_target_wig) {
            error "riboformer_reference_wig and riboformer_target_wig are required for riboformer"
        }
        // For bundled mode, the in-image dataset is referenced directly by name
        // and no external input dir is staged. Pass conf/ as a harmless placeholder
        // so Nextflow's path input is satisfied; the module's bash skips it.
        def input_ch = params.riboformer_bundled_dataset
            ? Channel.fromPath("${projectDir}/conf", type: 'dir', checkIfExists: true)
            : Channel.fromPath(params.riboformer_input, type: 'dir', checkIfExists: true)
        RIBOFORMER(
            input_ch,
            params.riboformer_model,
            params.riboformer_reference_wig,
            params.riboformer_target_wig
        )
    }

    if (params.ribotie_input) {
        if (!params.ribotie_config) {
            error "ribotie_config (YAML file) is required when ribotie_input is set"
        }
        RIBOTIE(
            Channel.fromPath(params.ribotie_input,  type: 'dir',  checkIfExists: true),
            Channel.fromPath(params.ribotie_config, type: 'file', checkIfExists: true)
        )
    }

    if (params.seq2ribo_input) {
        if (params.device == 'cpu') {
            log.warn "seq2ribo requires a GPU — skipping under CPU mode"
        } else {
            SEQ2RIBO(
                Channel.fromPath(params.seq2ribo_input, checkIfExists: true),
                params.seq2ribo_task,
                params.seq2ribo_cell_line
            )
        }
    }

    if (params.translationai_input) {
        TRANSLATIONAI(Channel.fromPath(params.translationai_input, checkIfExists: true))
    }

    if (params.saluki_input) {
        SALUKI(
            Channel.fromPath(params.saluki_input, checkIfExists: true),
            params.saluki_species
        )
    }

    if (params.codontransformer_input) {
        CODONTRANSFORMER(
            Channel.fromPath(params.codontransformer_input, checkIfExists: true),
            params.codontransformer_organism
        )
    }

    // ----- RNA Foundation Models -----

    if (params.rnafm_input) {
        RNAFM(Channel.fromPath(params.rnafm_input, checkIfExists: true))
    }

    if (params.rnafm_finetune_input) {
        if (!params.rnafm_finetune_label) {
            error "rnafm_finetune_label is required when rnafm_finetune_input is set"
        }
        if (params.rnafm_finetune_embeddings) {
            RNAFM_FINETUNE_FROM_EMB(
                Channel.of(tuple(
                    [name: 'rnafm', label_col: params.rnafm_finetune_label,
                     epochs: params.rnafm_finetune_epochs, lr: params.rnafm_finetune_lr,
                     head_type: params.rnafm_finetune_head_type,
                     task: params.rnafm_finetune_task],
                    file(params.rnafm_finetune_input, checkIfExists: true),
                    file(params.rnafm_finetune_embeddings, checkIfExists: true)
                ))
            )
        } else {
            if (params.rnafm_finetune_head_type == 'xgboost') {
                error "XGBoost head requires precomputed embeddings — set --rnafm_finetune_embeddings to use the FINETUNE_HEAD_ONLY path"
            }
            RNAFM_FINETUNE(Channel.fromPath(params.rnafm_finetune_input, checkIfExists: true))
        }
    }

    if (params.rinalmo_input) {
        RINALMO(Channel.fromPath(params.rinalmo_input, checkIfExists: true))
    }

    if (params.rinalmo_finetune_input) {
        if (!params.rinalmo_finetune_label) {
            error "rinalmo_finetune_label is required when rinalmo_finetune_input is set"
        }
        if (params.rinalmo_finetune_embeddings) {
            RINALMO_FINETUNE_FROM_EMB(
                Channel.of(tuple(
                    [name: 'rinalmo', label_col: params.rinalmo_finetune_label,
                     epochs: params.rinalmo_finetune_epochs, lr: params.rinalmo_finetune_lr,
                     head_type: params.rinalmo_finetune_head_type,
                     task: params.rinalmo_finetune_task],
                    file(params.rinalmo_finetune_input, checkIfExists: true),
                    file(params.rinalmo_finetune_embeddings, checkIfExists: true)
                ))
            )
        } else {
            if (params.rinalmo_finetune_head_type == 'xgboost') {
                error "XGBoost head requires precomputed embeddings — set --rinalmo_finetune_embeddings to use the FINETUNE_HEAD_ONLY path"
            }
            RINALMO_FINETUNE(Channel.fromPath(params.rinalmo_finetune_input, checkIfExists: true))
        }
    }

    if (params.ernierna_input) {
        ERNIERNA(Channel.fromPath(params.ernierna_input, checkIfExists: true))
    }

    if (params.ernierna_finetune_input) {
        if (!params.ernierna_finetune_label) {
            error "ernierna_finetune_label is required when ernierna_finetune_input is set"
        }
        if (params.ernierna_finetune_embeddings) {
            ERNIERNA_FINETUNE_FROM_EMB(
                Channel.of(tuple(
                    [name: 'ernierna', label_col: params.ernierna_finetune_label,
                     epochs: params.ernierna_finetune_epochs, lr: params.ernierna_finetune_lr,
                     head_type: params.ernierna_finetune_head_type,
                     task: params.ernierna_finetune_task],
                    file(params.ernierna_finetune_input, checkIfExists: true),
                    file(params.ernierna_finetune_embeddings, checkIfExists: true)
                ))
            )
        } else {
            if (params.ernierna_finetune_head_type == 'xgboost') {
                error "XGBoost head requires precomputed embeddings — set --ernierna_finetune_embeddings to use the FINETUNE_HEAD_ONLY path"
            }
            ERNIERNA_FINETUNE(Channel.fromPath(params.ernierna_finetune_input, checkIfExists: true))
        }
    }

    if (params.orthrus_input) {
        if (params.device == 'cpu') {
            log.warn "Orthrus requires a GPU — skipping under CPU mode"
        } else {
            ORTHRUS(Channel.fromPath(params.orthrus_input, checkIfExists: true))
        }
    }

    if (params.orthrus_finetune_input) {
        if (!params.orthrus_finetune_label) {
            error "orthrus_finetune_label is required when orthrus_finetune_input is set"
        }
        if (params.orthrus_finetune_embeddings) {
            // Embeddings shortcut runs in the CPU-only finetune-head image,
            // so it works under both -profile cpu and gpu.
            ORTHRUS_FINETUNE_FROM_EMB(
                Channel.of(tuple(
                    [name: 'orthrus', label_col: params.orthrus_finetune_label,
                     epochs: params.orthrus_finetune_epochs, lr: params.orthrus_finetune_lr,
                     head_type: params.orthrus_finetune_head_type,
                     task: params.orthrus_finetune_task],
                    file(params.orthrus_finetune_input, checkIfExists: true),
                    file(params.orthrus_finetune_embeddings, checkIfExists: true)
                ))
            )
        } else if (params.device == 'cpu') {
            log.warn "Orthrus fine-tune requires a GPU — skipping under CPU mode"
        } else {
            if (params.orthrus_finetune_head_type == 'xgboost') {
                error "XGBoost head requires precomputed embeddings — set --orthrus_finetune_embeddings to use the FINETUNE_HEAD_ONLY path"
            }
            ORTHRUS_FINETUNE(Channel.fromPath(params.orthrus_finetune_input, checkIfExists: true))
        }
    }

    if (params.rnaernie_input) {
        RNAERNIE(Channel.fromPath(params.rnaernie_input, checkIfExists: true))
    }

    if (params.rnaernie_finetune_input) {
        if (!params.rnaernie_finetune_label) {
            error "rnaernie_finetune_label is required when rnaernie_finetune_input is set"
        }
        if (params.rnaernie_finetune_embeddings) {
            RNAERNIE_FINETUNE_FROM_EMB(
                Channel.of(tuple(
                    [name: 'rnaernie', label_col: params.rnaernie_finetune_label,
                     epochs: params.rnaernie_finetune_epochs, lr: params.rnaernie_finetune_lr,
                     head_type: params.rnaernie_finetune_head_type,
                     task: params.rnaernie_finetune_task],
                    file(params.rnaernie_finetune_input, checkIfExists: true),
                    file(params.rnaernie_finetune_embeddings, checkIfExists: true)
                ))
            )
        } else {
            if (params.rnaernie_finetune_head_type == 'xgboost') {
                error "XGBoost head requires precomputed embeddings — set --rnaernie_finetune_embeddings to use the FINETUNE_HEAD_ONLY path"
            }
            RNAERNIE_FINETUNE(Channel.fromPath(params.rnaernie_finetune_input, checkIfExists: true))
        }
    }

    if (params.plantrnafm_input) {
        PLANTRNAFM(Channel.fromPath(params.plantrnafm_input, checkIfExists: true))
    }

    if (params.splicebert_input) {
        SPLICEBERT(Channel.fromPath(params.splicebert_input, checkIfExists: true))
    }

    if (params.pangolin_variants) {
        if (!params.pangolin_reference_fasta) {
            error "pangolin_reference_fasta is required when pangolin_variants is set"
        }
        if (!params.pangolin_annotation_db) {
            error "pangolin_annotation_db is required when pangolin_variants is set " +
                  "(build via upstream scripts/create_db.py from a GTF; see docs/models/Pangolin.md)"
        }
        PANGOLIN(
            Channel.fromPath(params.pangolin_variants, checkIfExists: true),
            Channel.fromPath(params.pangolin_reference_fasta, checkIfExists: true),
            Channel.fromPath(params.pangolin_annotation_db, checkIfExists: true)
        )
    }

    if (params.spliceai_vcf) {
        if (!params.spliceai_reference_fasta) {
            error "spliceai_reference_fasta is required when spliceai_vcf is set"
        }
        // SpliceAI's -A flag accepts a builtin keyword ('grch37'/'grch38') OR
        // a path to a custom GENCODE-style TSV. We always pass a tuple of
        // (keyword-or-path, staged-file). Custom file → real path; builtin →
        // empty NO_FILE placeholder so Nextflow has something to stage.
        def anno = params.spliceai_annotation ?: 'grch38'
        def anno_is_builtin = anno == 'grch37' || anno == 'grch38'
        def anno_file = anno_is_builtin
            ? file("${projectDir}/assets/NO_FILE", checkIfExists: true)
            : file(anno, checkIfExists: true)
        SPLICEAI(
            Channel.fromPath(params.spliceai_vcf, checkIfExists: true),
            Channel.fromPath(params.spliceai_reference_fasta, checkIfExists: true),
            Channel.value([anno, anno_file])
        )
    }

    if (params.plantrnafm_finetune_input) {
        if (!params.plantrnafm_finetune_label) {
            error "plantrnafm_finetune_label is required when plantrnafm_finetune_input is set"
        }
        if (params.plantrnafm_finetune_embeddings) {
            PLANTRNAFM_FINETUNE_FROM_EMB(
                Channel.of(tuple(
                    [name: 'plantrnafm', label_col: params.plantrnafm_finetune_label,
                     epochs: params.plantrnafm_finetune_epochs, lr: params.plantrnafm_finetune_lr,
                     head_type: params.plantrnafm_finetune_head_type,
                     task: params.plantrnafm_finetune_task],
                    file(params.plantrnafm_finetune_input, checkIfExists: true),
                    file(params.plantrnafm_finetune_embeddings, checkIfExists: true)
                ))
            )
        } else {
            if (params.plantrnafm_finetune_head_type == 'xgboost') {
                error "XGBoost head requires precomputed embeddings — set --plantrnafm_finetune_embeddings to use the FINETUNE_HEAD_ONLY path"
            }
            PLANTRNAFM_FINETUNE(Channel.fromPath(params.plantrnafm_finetune_input, checkIfExists: true))
        }
    }

    if (params.calm_input) {
        CALM(Channel.fromPath(params.calm_input, checkIfExists: true))
    }

    if (params.calm_finetune_input) {
        if (!params.calm_finetune_label) {
            error "calm_finetune_label is required when calm_finetune_input is set"
        }
        if (params.calm_finetune_embeddings) {
            CALM_FINETUNE_FROM_EMB(
                Channel.of(tuple(
                    [name: 'calm', label_col: params.calm_finetune_label,
                     epochs: params.calm_finetune_epochs, lr: params.calm_finetune_lr,
                     head_type: params.calm_finetune_head_type,
                     task: params.calm_finetune_task],
                    file(params.calm_finetune_input, checkIfExists: true),
                    file(params.calm_finetune_embeddings, checkIfExists: true)
                ))
            )
        } else {
            if (params.calm_finetune_head_type == 'xgboost') {
                error "XGBoost head requires precomputed embeddings — set --calm_finetune_embeddings to use the FINETUNE_HEAD_ONLY path"
            }
            CALM_FINETUNE(Channel.fromPath(params.calm_finetune_input, checkIfExists: true))
        }
    }

    if (params.mrnabert_input) {
        MRNABERT(Channel.fromPath(params.mrnabert_input, checkIfExists: true))
    }

    if (params.mrnabert_finetune_input) {
        if (!params.mrnabert_finetune_label) {
            error "mrnabert_finetune_label is required when mrnabert_finetune_input is set"
        }
        if (params.mrnabert_finetune_embeddings) {
            MRNABERT_FINETUNE_FROM_EMB(
                Channel.of(tuple(
                    [name: 'mrnabert', label_col: params.mrnabert_finetune_label,
                     epochs: params.mrnabert_finetune_epochs, lr: params.mrnabert_finetune_lr,
                     head_type: params.mrnabert_finetune_head_type,
                     task: params.mrnabert_finetune_task],
                    file(params.mrnabert_finetune_input, checkIfExists: true),
                    file(params.mrnabert_finetune_embeddings, checkIfExists: true)
                ))
            )
        } else {
            if (params.mrnabert_finetune_head_type == 'xgboost') {
                error "XGBoost head requires precomputed embeddings — set --mrnabert_finetune_embeddings to use the FINETUNE_HEAD_ONLY path"
            }
            MRNABERT_FINETUNE(Channel.fromPath(params.mrnabert_finetune_input, checkIfExists: true))
        }
    }

    if (params.hydrarna_input) {
        if (params.device == 'cpu') {
            log.warn "HydraRNA requires a GPU — skipping under CPU mode"
        } else {
            HYDRARNA(Channel.fromPath(params.hydrarna_input, checkIfExists: true))
        }
    }

    if (params.hydrarna_finetune_input) {
        if (!params.hydrarna_finetune_label) {
            error "hydrarna_finetune_label is required when hydrarna_finetune_input is set"
        }
        if (params.hydrarna_finetune_embeddings) {
            // Embeddings shortcut runs in the CPU-only finetune-head image,
            // so it works under both -profile cpu and gpu.
            HYDRARNA_FINETUNE_FROM_EMB(
                Channel.of(tuple(
                    [name: 'hydrarna', label_col: params.hydrarna_finetune_label,
                     epochs: params.hydrarna_finetune_epochs, lr: params.hydrarna_finetune_lr,
                     head_type: params.hydrarna_finetune_head_type,
                     task: params.hydrarna_finetune_task],
                    file(params.hydrarna_finetune_input, checkIfExists: true),
                    file(params.hydrarna_finetune_embeddings, checkIfExists: true)
                ))
            )
        } else if (params.device == 'cpu') {
            log.warn "HydraRNA fine-tune requires a GPU — skipping under CPU mode"
        } else {
            if (params.hydrarna_finetune_head_type == 'xgboost') {
                error "XGBoost head requires precomputed embeddings — set --hydrarna_finetune_embeddings to use the FINETUNE_HEAD_ONLY path"
            }
            HYDRARNA_FINETUNE(Channel.fromPath(params.hydrarna_finetune_input, checkIfExists: true))
        }
    }

    // ----- RNA Structure -----

    if (params.rnaformer_input) {
        RNAFORMER(Channel.fromPath(params.rnaformer_input, checkIfExists: true))
    }

    if (params.rhofold_input) {
        RHOFOLD(Channel.fromPath(params.rhofold_input, checkIfExists: true))
    }

    if (params.spotrna_input) {
        SPOTRNA(Channel.fromPath(params.spotrna_input, checkIfExists: true))
    }

    if (params.drfold2_input) {
        if (params.device == 'cpu') {
            log.warn "DRfold2 requires a GPU — skipping under CPU mode"
        } else {
            DRFOLD2(Channel.fromPath(params.drfold2_input, checkIfExists: true))
        }
    }

    // ----- RNA Modification -----

    if (params.multirm_input) {
        MULTIRM(Channel.fromPath(params.multirm_input, checkIfExists: true))
    }

    // ----- mRNA Design -----

    if (params.utrlm_input) {
        UTRLM(Channel.fromPath(params.utrlm_input, checkIfExists: true))
    }

    if (params.utrlm_finetune_input) {
        if (!params.utrlm_finetune_label) {
            error "utrlm_finetune_label is required when utrlm_finetune_input is set"
        }
        UTRLM_FINETUNE(Channel.fromPath(params.utrlm_finetune_input, checkIfExists: true))
    }
}
