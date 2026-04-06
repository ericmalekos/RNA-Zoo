#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

/*
========================================================================================
    RNAZoo: a model zoo for riboseq / translation-efficiency prediction
========================================================================================
*/

include { RNAZOO } from './workflows/rnazoo'

workflow {
    RNAZOO()
}
