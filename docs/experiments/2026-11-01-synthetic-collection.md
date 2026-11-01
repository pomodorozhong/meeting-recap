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

### Recap with an exact transcript

The first handoff recap propagated misrecognized task terms. Before running this diagnostic, fix both inputs and the scoring rule. For handoff and logistics, feed the original timed script with correct speaker IDs to the same pipeline summary stage. Keep the model, prompts and frozen checks identical. A check passes only if its subject, outcome and any specified owner and deadline survive. Report partial matches separately. This isolates errors that persist even when upstream text and attribution are exact.

### Repeatability and first-use cost

The first clean handoff included substantial first-use overhead, and the two full-size ASRs reversed order across recordings. Repeat all three ASRs twice on the identical clean handoff and on identical digital silence after the first pass. Keep each model's original runner, interpreter, language and word-timestamp settings. Compare the three normalized text outputs, error counts and wall times for each model/input. Treat a single improvement on a degraded pair as descriptive.

### Follow-up for silent inputs and long pauses

After the held-out base run, register an exploratory repair for exact digital silence. Find runs of at least five seconds of zero-valued PCM16 samples. On all-zero input return an empty transcript without loading an ASR model. Otherwise split only at those spans, retaining 250 ms at each speech edge. Run the same three pinned ASRs on the resulting stocktake chunks, shift word and segment times back to the original timeline, and compare CER, pause timestamps, wall time and footprint with the unmodified base runs. Scan all seven WAVs and check which ones this rule actually changes. This follow-up uses stocktake for development and needs a new independent sparse recording for confirmation.

## Reproduce

The [collection instructions](../../experiments/synthetic-call/README.md#recording-collection-and-unattended-benchmark) cover generating the seven WAVs, loading the pinned models and running the whole matrix with one command. Each additional condition has its own audio SHA-256 and a matching text and speaker reference. The original planning recording matched the repository's published digest. Rebuilding the three derived controls reproduced their WAV, text and speaker intervals byte for byte. On a different MLX build, score against the freshly generated references.

The supplementary timing and turn-order checks reuse the base pipeline outputs. The review skill at baseline `01eb50d` creates a sealed evaluation and validates its dataset independently for each speech recording. Code and input recipes for this round are at `cb784e9`. Commit `68e2da3` adds an output-location check before running them. All fixture audio and raw model outputs stay local.

## Runtime and memory

The benchmark ran one inference process at a time on an M2 Pro with 16 GB, macOS 26.6.2, Python 3.12.13 and MLX 0.32.4. ASR wall time includes Python process startup, model loading and decoding. Diarizer wall time includes command startup and model loading. Peak memory is the per-process macOS peak memory footprint reported by `/usr/bin/time -l`, in decimal GB. It includes memory that peak resident set size alone can miss.

On the 329.88-second planning input, the baseline Whisper ASR took 43.37 s and Sortformer 136.90 s. Who took 1.23 s on the same converted input. Their ASR-plus-diarization stage sums are 180.27 s and 44.60 s, respectively. These sums exclude conversion, Markdown rendering and recap generation. The two clean new end-to-end runs took 150.2 s (61 s of handoff audio, including first-use startup) and 71.2 s (56 s of logistics audio).

## Results

### Text and speakers

Character error rate (CER) is the Levenshtein edit count divided by script characters, after OpenCC Traditional-to-Simplified conversion, case folding and removal of punctuation and whitespace. Numbers, English spellings and homophones receive no special equivalences. Overlapping utterances use their scripted start order. A lower score means fewer edits to recover the script.

Speaker-time error is (missed + false-alarm + confused speaker-seconds) divided by reference speaker-seconds, with one-to-one maximum-overlap label mapping per recording, overlap included and zero collar. Generated turn intervals include pauses inside each utterance, so the timing metric can penalize a model that correctly detects an internal pause. The separate word-label metric uses the repository scorer's more forgiving many-to-one mapping. All are script-based measurements.

### Alternative diarizers

| Local runner | Handoff speaker-time error | Logistics speaker-time error |
| --- | ---: | ---: |
| Community-1 automatic count | 57.1% | 70.5% |
| Community-1 given the correct count | 57.1% | 60.6% |
| LS-EEND DIHARD III | 57.7% | 53.1% |
| LS-EEND AMI | 52.7% | 45.4% |
| LS-EEND CALLHOME | 33.1% | 50.6% |
| LS-EEND DIHARD II | 57.7% | 49.3% |

These runs took 0.9–1.8 seconds each. Specifying how many people spoke sometimes fixed the label count while leaving most speaker-time errors in place. Each alternative had one run per recording.

### Recaps

The four handoff checks and five logistics checks were fixed before inference. An agent read the generated notes against the fictional script. Owner checks map the anonymous output labels back to script speakers before judging them. In the four-person run, the displayed labels C and D corresponded to script speakers D and C. A repeated statement counts once. These are targeted semantic checks, separate from transcript or diarization scores.
