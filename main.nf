#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

/*
========================================================================================
    RiboZoo: a model zoo for riboseq / translation-efficiency prediction
========================================================================================
*/

include { RIBOZOO } from './workflows/ribozoo'

workflow {
    RIBOZOO()
}
