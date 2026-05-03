# TranslationAI

Predict translation initiation sites (TIS), translation termination sites (TTS), and ORFs from mRNA sequence.

- **Paper:** [NAR 2025](https://academic.oup.com/nar/article/53/7/gkaf277/8112693)
- **Upstream:** https://github.com/rnasys/TranslationAI
- **License:** AGPL-3.0 (source code) + CC BY-NC 4.0 (model weights, non-commercial only)
- **Device:** CPU or GPU. Two image variants:
    - `rnazoo-translationai:latest` — CUDA-enabled (TF 1.15 GPU build, default with `-profile gpu`). Works on any GPU; older binary kernels PTX-JIT for compute capabilities >7.0 (Turing/Ampere/Ada/Hopper) on first kernel launch.
    - `rnazoo-translationai-cpu:latest` — CPU-only (smaller, used with `-profile cpu`)

## What it does

TranslationAI uses deep learning to identify translation initiation sites (TIS), translation termination sites (TTS), and complete ORFs in mRNA sequences. It scans each input mRNA and outputs site-level probability scores for where translation starts and stops, then assembles predicted ORFs from TIS/TTS pairs.

## Input format

FASTA file of mRNA sequences (DNA alphabet):

```
>chr3:28283123-28361264(+)(CMC1)(241, 568,)
GAGGGAACGGGTCCTGGCGGTGCTTTGCAAAGGGCCCGTGTTTCTGTTG...
>chr9:98997588-99064434(-)(HSD17B3)(48, 978,)
TACACAGAGAGCCACGGCCAGGGCTGAAACAGTCTGTTGAGTGCAGCCAT...
```

Headers can be in any format. The optional `(start, stop,)` notation in the example above is used by the upstream tool for validation but is not required.

## Output format

Three text files per input:

1. **`*_predTIS_*.txt`** -- predicted TIS positions and probabilities:
   ```
   >chr3:28283123-28361264(+)(CMC1)(241, 568,)	241,0.8824475854635239
   ```
   Format: `header<TAB>position,probability`

2. **`*_predTTS_*.txt`** -- predicted TTS positions and probabilities (same format)

3. **`*_predORFs_*.txt`** -- predicted ORFs (TIS-TTS pairs with scores)

## Run with Docker

> See the [Direct Docker guide](../direct-docker.md) for the shared `docker run` recipe (UID, `HOME`, `USER` env vars, and GPU flag). Below are the model-specific parts.

```bash
# CPU
docker run --rm \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-translationai-cpu:latest \
  bash -c "cp /data/input.fa /tmp/input.fa && \
    translationai -I /tmp/input.fa -t 0.5,0.5 && \
    cp /tmp/input_pred*.txt /out/"

# GPU
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /path/to/input.fa:/data/input.fa \
  -v /path/to/output:/out \
  ghcr.io/ericmalekos/rnazoo-translationai:latest \
  bash -c "cp /data/input.fa /tmp/input.fa && \
    translationai -I /tmp/input.fa -t 0.5,0.5 && \
    cp /tmp/input_pred*.txt /out/"
```

## Run with Nextflow

```bash
nextflow run main.nf -profile docker,cpu \
  --translationai_input /path/to/input.fa
```

Only models with input provided will run — no ignore flags needed.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--translationai_tis_threshold` | `0.5` | TIS probability threshold (0-1) |
| `--translationai_tts_threshold` | `0.5` | TTS probability threshold (0-1) |

## Example output

**TIS predictions:**
```
>chr3:28283123-28361264(+)(CMC1)(241, 568,)	241,0.8824475854635239
>chr9:98997588-99064434(-)(HSD17B3)(48, 978,)	48,0.9925230294466019
>chr1:153175905-153177601(+)(LELP1)(123, 417,)	123,0.9739317893981934
```

Each line shows the predicted TIS position and its probability score. Higher scores indicate more confident predictions. The threshold parameters control which predictions are reported.
