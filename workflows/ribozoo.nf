/*
========================================================================================
    RIBOZOO workflow: dispatch input to each enabled model module
========================================================================================
*/

include { RIBONN      } from '../modules/local/ribonn'
include { RIBOFORMER  } from '../modules/local/riboformer'
include { RIBOTIE     } from '../modules/local/ribotie'
include { SEQ2RIBO    } from '../modules/local/seq2ribo'
include { SALUKI            } from '../modules/local/saluki'
include { TRANSLATIONAI    } from '../modules/local/translationai'
include { CODONTRANSFORMER } from '../modules/local/codontransformer'

workflow RIBOZOO {
    main:

    // ----- sequence → prediction track -----

    if (!params.ignore_ribonn) {
        if (params.ribonn_input == null) {
            error "params.ribonn_input is required unless --ignore_ribonn is set"
        }
        ribonn_ch = Channel.fromPath(params.ribonn_input, checkIfExists: true)
        RIBONN(ribonn_ch)
    }

    // ----- ribo-seq refinement / correction track -----

    if (!params.ignore_riboformer) {
        if (params.riboformer_input == null) {
            error "params.riboformer_input is required unless --ignore_riboformer is set"
        }
        if (params.riboformer_reference_wig == null || params.riboformer_target_wig == null) {
            error "params.riboformer_reference_wig and params.riboformer_target_wig are required unless --ignore_riboformer is set"
        }
        riboformer_ch = Channel.fromPath(params.riboformer_input, type: 'dir', checkIfExists: true)
        RIBOFORMER(
            riboformer_ch,
            params.riboformer_model,
            params.riboformer_reference_wig,
            params.riboformer_target_wig
        )
    }

    if (!params.ignore_ribotie) {
        if (params.ribotie_input == null || params.ribotie_config == null) {
            error "params.ribotie_input (directory) and params.ribotie_config (YAML file) are required unless --ignore_ribotie is set"
        }
        ribotie_input_ch  = Channel.fromPath(params.ribotie_input,  type: 'dir',  checkIfExists: true)
        ribotie_config_ch = Channel.fromPath(params.ribotie_config, type: 'file', checkIfExists: true)
        RIBOTIE(ribotie_input_ch, ribotie_config_ch)
    }

    if (!params.ignore_saluki) {
        if (params.saluki_input == null) {
            error "params.saluki_input (FASTA file with lowercase=UTR, uppercase=CDS) is required unless --ignore_saluki is set"
        }
        saluki_ch = Channel.fromPath(params.saluki_input, checkIfExists: true)
        SALUKI(saluki_ch, params.saluki_species)
    }

    if (!params.ignore_translationai) {
        if (params.translationai_input == null) {
            error "params.translationai_input (FASTA of mRNA sequences) is required unless --ignore_translationai is set"
        }
        translationai_ch = Channel.fromPath(params.translationai_input, checkIfExists: true)
        TRANSLATIONAI(translationai_ch)
    }

    // ----- codon design -----

    if (!params.ignore_codontransformer) {
        if (params.codontransformer_input == null) {
            error "params.codontransformer_input (FASTA of amino acid sequences) is required unless --ignore_codontransformer is set"
        }
        codontransformer_ch = Channel.fromPath(params.codontransformer_input, checkIfExists: true)
        CODONTRANSFORMER(codontransformer_ch, params.codontransformer_organism)
    }

    // ----- GPU-only models -----
    // seq2ribo requires CUDA; auto-skip under --profile cpu

    if (!params.ignore_seq2ribo) {
        if (params.device == 'cpu') {
            log.warn "seq2ribo requires a GPU — auto-skipping under --profile cpu"
        } else {
            if (params.seq2ribo_input == null) {
                error "params.seq2ribo_input (FASTA file) is required unless --ignore_seq2ribo is set"
            }
            seq2ribo_ch = Channel.fromPath(params.seq2ribo_input, checkIfExists: true)
            SEQ2RIBO(seq2ribo_ch, params.seq2ribo_task, params.seq2ribo_cell_line)
        }
    }
}
