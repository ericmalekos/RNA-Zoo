/*
========================================================================================
    TRANSLATIONAI module: predict TIS, TTS, and ORFs from mRNA sequence
    Upstream: https://github.com/rnasys/TranslationAI
    Paper: NAR 2025

    LICENSE: Source code is AGPL-3.0. Pretrained model weights are CC BY-NC 4.0
    (non-commercial only).
========================================================================================
*/

process TRANSLATIONAI {
    tag "translationai"
    label 'process_medium'

    input:
    path input_fasta

    output:
    path "*_predTIS_*.txt",  emit: tis_predictions
    path "*_predTTS_*.txt",  emit: tts_predictions
    path "*_predORFs_*.txt", emit: orf_predictions

    script:
    def tis_thresh = params.translationai_tis_threshold
    def tts_thresh = params.translationai_tts_threshold
    """
    # TranslationAI writes output files alongside the input FASTA.
    # Copy input to CWD so outputs land in the Nextflow task workdir.
    cp ${input_fasta} input.fa
    translationai -I input.fa -t ${tis_thresh},${tts_thresh}

    # Rename outputs to include the original filename for clarity
    for f in input_pred*.txt; do
        mv "\$f" "\${f/input/${input_fasta.baseName}}"
    done
    """
}
