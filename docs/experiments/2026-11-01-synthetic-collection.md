# 2026-11-01 synthetic recording collection

**Status** Runs in progress.

## Question

Which local ASR and speaker models keep their accuracy and speed when a meeting changes from two voices to four, speakers interrupt each other, or one microphone is degraded? Does the saved-audio pipeline recover the decisions and assignments on new subjects?

## Goal and assumptions

Builds on the [synthetic planning call](../../experiments/synthetic-call/README.md), the [MLX ASR comparison](2026-10-24-transcription-variants.md) and [diarizer sweep](2026-10-24-diarizer-comparison.md). Compare per-recording errors and serial warm-cache wall time on the M2 Pro / 16 GB. Favor the faster model if its accuracy holds across distinct scripts. Expect overlap to hurt both text and speaker attribution. Use pinned, cached models and run one inference process at a time.

## Input

The existing three-speaker planning call is a baseline. Add a two-speaker incident handoff and a four-speaker event logistics call in Mandarin with English terms, using the existing pinned Qwen3-TTS preset voices and seed 7. Pair the handoff with an attenuated, noisy channel mix and the logistics call with an interruption mix. The controls reuse identical synthesized turns. Include digital silence to measure spurious output.

## Plan

Use recording IDs planning, handoff, handoff-channel, logistics, logistics-overlap and silence. The ASR and diarizer run IDs combine recording and model names. Score whole recordings against their own generated transcript and segment files. These scripted references require no clip selection, listening session or private dataset.

| Runs | Models and settings | Entry point |
| --- | --- | --- |
| Text on all inputs | MLX Whisper Large v3 and Breeze-ASR-25, forced Chinese, word times, independent chunks, pins in [runners](../runners.md) | MLX runner or pipeline ASR stage |
| Speakers on all inputs | Sortformer and Who int8, revisions and weight digests in the [pipeline pins](../../experiments/pipelines/whisper-sortformer/pins.py) | Pipeline Swift CLIs |
| Diarizer alternatives on both clean new scripts | FluidAudio Community-1, auto and oracle count, plus LS-EEND dihard3, ami, callhome and dihard2. Record loaded weight digests | diarexp and fluidaudiocli, [build instructions](../runners.md) |
| Attribution | Cross both transcripts with both primary diarizers and compare word-at-time label agreement. Also measure model-only time error with a one-to-one speaker mapping, including overlap | Collection scorer |
| End-to-end recaps on the two clean new scripts | Default Whisper / Sortformer / Qwen3.5-9B 4-bit pipeline, revisions in pipeline pins | recap.py run |

Freeze these recap checks before inference. For the handoff, look for the decision to keep the retry limit at two, Speaker B's log export by noon, Speaker A's rollback checklist by Friday and the unresolved cause of the timeout. For logistics, look for the indoor venue decision, Speaker B's sign count by Wednesday, Speaker C's projector test on Thursday, Speaker D's accessibility map by Friday and the unresolved interpreter budget. Judge presence, correct attribution and dates from the generated notes. Count unsupported claims separately.

### Registered extension

Add a faster ASR candidate because the original matrix compares two full-size models. Run the same MLX CLI and decoding settings with [Whisper Large v3 Turbo Q4](https://huggingface.co/mlx-community/whisper-large-v3-turbo-q4/tree/660c343bbf4e52ac257f0b7d952e5388e6f93bef), revision `660c343bbf4e52ac257f0b7d952e5388e6f93bef`, on all six recordings. Download the weights once before timing. Compare character errors, wall time and footprint.

Also test whether the actual attached transcript keeps turn order. Register the two full-size ASR runs and both primary diarizers for every non-silent input in an isolated synthetic review dataset. Use `review.py known` with its 30-second window and 0.3-second minimum, then compare the original diarizers and the skill's word, segment and line attachment methods (1-second maximum gap). Use reference IDs `ref-<case>` and evaluation IDs `eval-<case>`. No listening session is needed. Keep any refused inputs visible. This adds a text-delivery check beyond agreement at ASR word timestamps.

### Held-out stocktake

Before seeing the cross-model rankings, reserve one additional independent script for confirmation. It covers the missing one-speaker case and inserts 18 seconds of silence between two spoken sections. Run the same three ASRs and two primary diarizers on it after the initial matrix, using the same metrics and settings. Count timestamped word midpoints strictly inside the long scripted gap as a silence diagnostic. Compare the existing candidates without tuning on this script.

## Restart from scratch

Generate both scripts and the two paired conditions, then run the matrix serially. Use each generated call's own references after verifying its audio digest. Commands and per-case timings will accompany results.

## Runtime and memory

Pending.

## Results

Pending. Character error rate will use edit distance after script conversion, case folding and punctuation/space removal. Report absolute false characters on silence. TTS turn boundaries include short pauses within synthesized utterances, which can inflate missed speaker time. Paired variants share content and must not be counted as independent meetings.

## Decision and open questions

Pending. These synthetic voices and read speech cover only part of the target microphone and meeting conditions.
