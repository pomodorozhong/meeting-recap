# 2026-11-01 synthetic recording collection

**Status** Complete.

Seven files cover 10 minutes 14 seconds of audio, four distinct scripts, one through four speakers, two matched stress tests and digital silence. Turbo Q4 was the fastest ASR on every input, and matched or beat full Whisper's CER on all six speech recordings. Breeze was substantially better on the sparse single-speaker holdout. [Per-case metrics and audio digests](2026-11-01-synthetic-collection-results.json).

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

### Usable fast pipeline

Turbo Q4 matched or improved full Whisper CER on the first five speech mixes, at lower footprint. Verify the combination in the ordinary saved-audio pipeline with an opt-in ASR selector. Run `recap.py run AUDIO OUT --asr turbo-q4 --diarizer who` on the clean handoff and logistics recordings, with the default Qwen summary. Use the existing checks, original audio digests, fitted speaker identities, per-stage timing and footprint. Compare against the two completed full Whisper / Sortformer pipelines and keep the defaults fixed.

## Reproduce

The [collection instructions](../../experiments/synthetic-call/README.md#recording-collection-and-unattended-benchmark) cover generating the seven WAVs, loading the pinned models and running the whole matrix with one command. Each additional condition has its own audio SHA-256 and a matching text and speaker reference. The original planning recording matched the repository's published digest. Rebuilding the three derived controls reproduced their WAV, text and speaker intervals byte for byte. On a different MLX build, score against the freshly generated references.

The supplementary timing and turn-order checks reuse the base pipeline outputs. The review skill at baseline `01eb50d` creates a sealed evaluation and validates its dataset independently for each speech recording. Code and input recipes for this round are at `cb784e9`. Commit `68e2da3` adds an output-location check, `ed76684` adds the exact-silence diagnostic and `b73b045` exposes the pinned fast ASR in the normal pipeline. All fixture audio and raw model outputs stay local.

## Runtime and memory

The benchmark ran one inference process at a time on an M2 Pro with 16 GB, macOS 26.6.2, Python 3.12.13 and MLX 0.32.4. ASR wall time includes Python process startup, model loading and decoding. Diarizer wall time includes command startup and model loading. Peak memory is the per-process macOS peak memory footprint reported by `/usr/bin/time -l`, in decimal GB. It includes memory that peak resident set size alone can miss.

On the 329.88-second planning input, the baseline Whisper ASR took 43.37 s and Sortformer 136.90 s. Who took 1.23 s on the same converted input. Their ASR-plus-diarization stage sums are 180.27 s and 44.60 s, respectively. These sums exclude conversion, Markdown rendering and recap generation. The two clean new end-to-end runs took 150.2 s (61 s of handoff audio, including first-use startup) and 71.2 s (56 s of logistics audio).

## Results

### Text and speakers

Character error rate (CER) is the Levenshtein edit count divided by script characters, after OpenCC Traditional-to-Simplified conversion, case folding and removal of punctuation and whitespace. Numbers, English spellings and homophones receive no special equivalences. Overlapping utterances use their scripted start order. A lower score means fewer edits to recover the script.

Speaker-time error is (missed + false-alarm + confused speaker-seconds) divided by reference speaker-seconds, with one-to-one maximum-overlap label mapping per recording, overlap included and zero collar. Generated turn intervals include pauses inside each utterance, so the timing metric can penalize a model that correctly detects an internal pause. The separate word-label metric uses the repository scorer's more forgiving many-to-one mapping. All are script-based measurements.

| Recording | Script characters | Whisper CER | Breeze CER | Turbo Q4 CER | Sortformer speaker-time error | Who speaker-time error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| handoff | 223 | 6.3% | 27.8% | 6.3% | 11.5% | 7.1% |
| handoff-channel | 223 | 12.6% | 11.2% | 12.1% | 19.0% | 4.0% |
| logistics | 197 | 15.2% | 7.6% | 12.7% | 15.7% | 22.7% |
| logistics-overlap | 197 | 16.2% | 27.4% | 14.2% | 12.1% | 25.2% |
| planning | 1377 | 4.9% | 12.2% | 4.2% | 14.9% | 6.1% |
| stocktake | 116 | 41.4% | 14.7% | 41.4% | 11.2% | 28.7% |

On the four distinct scripts, micro-averaged CER was 7.6% for Turbo Q4 (145/1,913 edits), 8.3% for full Whisper (159/1,913) and 13.7% for Breeze (262/1,913). The planning call supplies 72% of these characters. The two derived mixes share their parents' words and are omitted from this aggregate. Overlap raised Breeze's error from 7.6% to 27.4%. On the quiet-microphone mix, Breeze made fewer errors than on the clean version. These are observations on the paired recordings, each with one fixed noise realization or overlap pattern.

### Speed, memory and repeatability

| ASR on 329.88 s of planning audio | Wall time | Peak process footprint | CER |
| --- | ---: | ---: | ---: |
| Turbo Q4 | 22.32 s | 4.26 GB | 4.2% |
| Full Whisper | 43.37 s | 9.29 GB | 4.9% |
| Breeze | 90.84 s | 13.09 GB | 12.2% |

The two extra decodes on the clean handoff and on digital silence reproduced each model's original normalized text in all 12 comparisons. For the handoff, full Whisper took 73.18 s on first use and 11.97 / 11.89 s on replay. Breeze took 83.98 s and 20.31 / 21.00 s. Turbo Q4 took 7.24 s and 7.08 / 7.15 s. The first two were the first uses of their respective freshly provisioned Python environments. A Swift build briefly overlapped the start of that first pipeline, and model cache preparation overlapped part of it. Treat its elapsed time as a cold observation.

Across all seven inputs, Who took 4.15 s total and peaked at 0.28 GB. Sortformer took 265.50 s and peaked at 0.86 GB. Who merged two voices in the clean four-person run and split the one voice in the holdout. Sortformer recovered four and one labels respectively. On the overlap mix both produced four labels, with markedly different speaker-time error.

### Silence and pauses

On 12 s of digital silence, full Whisper emitted 20 normalized characters, Turbo Q4 emitted 35 and Breeze emitted zero. Both diarizers reported zero speaker-seconds. CER is undefined for this input. A five-second exact-zero gate returned empty text for all three without invoking a model. Five speech recordings passed through byte-for-byte, with no inference repeated for them.

Only stocktake contained a qualifying internal gap. Splitting it into two chunks reduced full Whisper from 48 to 18 edits (41.4% to 15.5%) and Turbo Q4 from 48 to 21 (41.4% to 18.1%). Breeze went from 17 to 25 (14.7% to 21.6%). Split times were 12.71, 6.87 and 14.03 s for full Whisper, Turbo Q4 and Breeze respectively. These sum chunk process time and in-process scan/write time. Full Whisper and Turbo placed zero word midpoints in the long gap before splitting, Breeze placed three. All three placed one midpoint inside its edge after restoring timestamps. A midpoint in a gap can be a timestamp error. Exact-zero detection does not cover pauses with room noise. This exploratory result needs another sparse recording.

### Speaker turn order and delivered text

The review skill validated six sealed synthetic datasets. All 72 attachments and 12 raw diarizer outputs were scored, with no registration failures or excluded clips. Each speech case used about 30-second windows and its own fitted one-to-one label map. Metric scores count recovered turns in sequence and wholly correct clips. Adjacent same-speaker intervals collapse, so the six stocktake utterances yield two reference turns across two clips.

On planning, raw Sortformer recovered 67/72 turns and 7/10 complete clips, compared with Who at 64/72 and 6/10. Whisper plus Sortformer recovered 66 turns with word attachment, 65 with segment attachment and 63 with line-end lookup. On overlapping logistics, Whisper plus Who recovered 14/14 with words and 11/14 with either coarser method. The full results include counterexamples where segment attachment won. Word overlap remains the useful general setting.

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

| Preregistered check | Pipeline transcript | Exact transcript |
| --- | --- | --- |
| Handoff, keep the retry limit at two | Pass | Pass |
| Handoff, B exports logs by noon | Partial. Owner survived, destination and deadline were garbled | Pass |
| Handoff, A prepares rollback checklist by Friday | Partial. Owner and day survived, checklist subject changed | Pass |
| Handoff, timeout cause remains unresolved | Pass in topics | Pass in topics |
| Logistics, choose indoor venue | Pass | Pass |
| Logistics, B counts signs by Wednesday | Partial. Owner and day survived, count narrowed to elevator signs | Pass |
| Logistics, C tests projector on Thursday | Pass after label mapping, with an unrelated corrupted equipment detail | Pass |
| Logistics, D delivers accessibility map by Friday | Partial. One map detail survived, accessibility and deadline were missing | Pass |
| Logistics, interpreter budget remains open | Partial. An open budget survived, its subject changed | Pass |

Four of nine checks passed in full from the pipeline transcript and nine of nine from the exact script. The notes can satisfy a targeted check and still introduce an error elsewhere in that item. In a separate audit of non-topic items, two handoff action rows and three logistics rows contained unsupported or garbled details. Neither exact-input recap contained those factual substitutions. Both input conditions still put a rejected or superseded option in the undecided-proposals section of each meeting. The exact-input handoff also listed two already-answered formulations as open while its topics correctly identified the underlying uncertainty. These judgments concern two fictional meetings and a single unblinded reader.

### Fast saved-audio pipeline

The ordinary `run --asr turbo-q4 --diarizer who` command produced a labeled transcript and a Qwen recap for both clean new scripts. On the handoff it took 47.05 s end to end, with 7.13 s in ASR, 1.31 s in diarization and 38.50 s in the recap. On logistics it took 44.00 s, with 6.23 s in ASR, 0.37 s in diarization and 37.29 s in the recap. The peak stage footprints were 6.74 and 6.72 GB. The full Whisper / Sortformer totals were 150.23 and 71.19 s respectively. The first handoff timing includes the cold start described above.

On handoff, the fast pipeline correctly attributed 205/209 aligned characters, versus 202/209 for the baseline. On logistics it correctly attributed 134/172, versus 144/167. In both fast recaps, the same four of nine checks passed in full. The handoff captured the log deadline, but the destination and the rollback term remained corrupted. On logistics, Who merged B and D. The sign-count owner could not be distinguished from the map owner, while the projector assignment and the venue decision survived. The notes also reopened the already-settled entrance question. Readable formatting and valid timestamps did not guarantee factual correctness.

## Decision and limits

Offer Turbo Q4 as the fast ASR option on this Mac. Pair it with Sortformer for four-speaker work where keeping people distinct matters, or use Who when diarization latency matters more. The collection supports keeping word-level overlap attachment. Use exact-zero splitting as an experimental diagnostic for sparse recordings. The clean-source recap controls show that improving text and speaker labeling can recover missed assignments, while proposal and open-question classification still need separate evaluation.

The seven recordings comprise four independent scripts, generated with four preset voices. A script is a reference for intended speech, so TTS pronunciation differences can also count as recognition errors. Counts and peak footprints describe this machine, model revisions and recording lengths. Private meetings, background conversation, voices sharing a room and calls beyond four people need independent evidence. Default pipeline settings remain as in decision 7.
