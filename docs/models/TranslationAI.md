# TranslationAI

Predict translation initiation sites (TIS), translation termination sites (TTS), and ORFs from mRNA sequence.

- **Paper:** [NAR 2025](https://academic.oup.com/nar/article/53/7/gkaf277/8112693)
- **Upstream:** https://github.com/rnasys/TranslationAI
- **License:** AGPL-3.0 (source code) + CC BY-NC 4.0 (model weights, non-commercial only)
- **Device:** CPU. The pipeline runs `rnazoo-translationai-cpu` under both profiles, because
  TranslationAI's command-line entry point hides every GPU (`CUDA_VISIBLE_DEVICES=-1`).

## What it does

A 32-layer dilated residual CNN, trained on human RefSeq protein-coding transcripts, scores every
mRNA position as a TIS or TTS (five models with 2,000 nt of context, averaged) and pairs in-frame
TIS and TTS calls into ORFs. Length is not capped.

## Input

FASTA with A, C, G, T or N only, each sequence on one line, and headers in upstream's layout
`>chrN:start-end(strand)(name)(TIS, TTS,)`; other headers stop the run.

```
>chr3:28283123-28361264(+)(CMC1)(241, 568,)
GAGGGAACGGGTCCTGGCGGTGCTTTGCAAAGGG...
```

## Output

In `results/translationai/`, named after the input and the thresholds: `<input>_predTIS_<t>.txt`
and `<input>_predTTS_<t>.txt` (the header, then `position,score` per site, best first), and
`<input>_predORFs_<t>_<t>.txt` (the header, then `TIS,TTS,TIS_score,TTS_score` per pair, best
product first; transcripts without a pair are left out). Positions are 0-based and mark the
first base of the start or stop codon.

Example (`translationai_test_predTIS_0.5.txt` from the test profile):

```
>chr3:28283123-28361264(+)(CMC1)(241, 568,)	241,0.8824475854635239
```

## Run with Docker

TranslationAI writes next to its input, so the command works on a copy in `/tmp`:

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -e USER=$(whoami) \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-translationai-cpu:latest \
  bash -c "cp /data/input.fa /tmp/input.fa && translationai -I /tmp/input.fa -t 0.5,0.5 && cp /tmp/input_pred*.txt /out/"
```

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu --translationai_input /path/to/input.fa
```

`-profile docker,gpu` runs the same CPU image. Results go to `results/translationai/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--translationai_input` | `null` | FASTA file |
| `--translationai_tis_threshold` | `0.5` | Below 1, the minimum TIS score; 1 or more, the number of top TIS per transcript |
| `--translationai_tts_threshold` | `0.5` | The same for TTS |

## Limitations

- An ORF pairs any predicted TIS with any predicted TTS downstream in the same frame, without
  checking for stop codons in between.
