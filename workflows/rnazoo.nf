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
include { RINALMO          } from '../modules/local/rinalmo'
include { ERNIERNA         } from '../modules/local/ernierna'
include { ORTHRUS          } from '../modules/local/orthrus'
include { RNAERNIE         } from '../modules/local/rnaernie'
include { RNAFORMER        } from '../modules/local/rnaformer'
include { RHOFOLD          } from '../modules/local/rhofold'
include { SPOTRNA          } from '../modules/local/spotrna'
include { MULTIRM          } from '../modules/local/multirm'
include { UTRLM            } from '../modules/local/utrlm'
include { UTRLM_FINETUNE   } from '../modules/local/utrlm_finetune'

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

    if (params.rinalmo_input) {
        RINALMO(Channel.fromPath(params.rinalmo_input, checkIfExists: true))
    }

    if (params.ernierna_input) {
        ERNIERNA(Channel.fromPath(params.ernierna_input, checkIfExists: true))
    }

    if (params.orthrus_input) {
        if (params.device == 'cpu') {
            log.warn "Orthrus requires a GPU — skipping under CPU mode"
        } else {
            ORTHRUS(Channel.fromPath(params.orthrus_input, checkIfExists: true))
        }
    }

    if (params.rnaernie_input) {
        RNAERNIE(Channel.fromPath(params.rnaernie_input, checkIfExists: true))
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
