# 2026-11-02: digital silence on the 17-recording synthetic collection

**Status:** complete

**Outcome:** On four generated recordings with a long pause made of exact digital zeros, decoding the speech on each side of the pause separately lowered total Mandarin error rates for full Whisper (9.98% to 6.43%) and Turbo (7.59% to 6.56%), barely changed their English rates, and made Breeze worse in both languages. A recording that is entirely digital zeros now skips recognition and the recap, because full Whisper and Turbo returned text on one. The split is an opt-in flag for full Whisper only, because only that version was checked through the pipeline, not because it beat Turbo; neither rule applies to quiet rooms, and neither was tested on a real recording.

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/synthetic-call/collection_setup.sh` |
| Run everything | `experiments/synthetic-call/collection_run.sh "$FIXTURES" "$RESULTS"` |
| Run only what this summary uses | The same command with `--step decode`, then `--step recaps`, `--step diarize`, `--step split` and `--step replays`, in that order |
| Check saved results without models | `uv run --project experiments/synthetic-call experiments/synthetic-call/collection_scores.py "$FIXTURES" "$RESULTS" > scores.json` |

The steps depend on each other. `split` compares against the whole-file output from `decode`. The silent-input run is part of `recaps`, which also runs the recap model on two spoken calls. The pause option is the first command in `replays`, and the rest of that step reads outputs from `recaps` and `diarize`.

- **It needs:** `FIXTURES`, the verified collection built by [`collection.py`](../../experiments/synthetic-call/README.md#seventeen-recording-collection), and `RESULTS`, a new absolute path outside Git.
- **It writes:** model outputs under `RESULTS`, and measurements in `RESULTS/scores.json`. [Several summaries share this one run](../../experiments/synthetic-call/README.md#compare-the-pipeline-on-this-collection), so the scorer needs every step's outputs, including `turns`. [The saved measurements](2026-11-02-synthetic-collection-results.json) are the committed copy.
- **Takes about:** 5.5 minutes for `split` in the saved timings. All timed steps total about 54 minutes; `turns` and `replays` weren't timed as steps.
- **By hand:** comparing `onboarding/pause-pipeline` with the experiment's `onboarding/split/whisper.json`. The scorer doesn't read the pause run and no committed script compares them, so its figures below aren't in the results file.
- **Expect to differ:** timings on any rerun, and possibly model text on another machine. The scorer recalculates from saved outputs, so it should match the committed file byte for byte. The [earlier combined write-up at `d182e52`](https://github.com/pomodorozhong/meeting-recap/blob/d182e52/docs/experiments/2026-11-02-synthetic-collection-pipeline.md), which is **not on `main`**, says a rerun of `replays` on 2026-11-03 matched the saved words and transcripts byte for byte, and that the other steps weren't rerun, so `split` hasn't been run through this entry point.

## Question

The pipeline's README describes this rule as aimed at digital edits and mutes, meaning stretches whose samples are exactly zero. Does decoding the speech on each side of a long stretch like that, instead of the whole file at once, reduce recognition errors in Mandarin and in English? And what should the pipeline do with a recording that is entirely zeros, given that text invented there would reach the recap?

- **Decision it informs:** whether to offer the split, for which recognizers, and whether silent input skips recognition.
- **Expected result:** no expected size of effect was stated. The plan's pass rule was to keep the split experimental "unless neither language regresses". The plan doesn't say whether that applies per recognizer. A second rule in the plan covered every candidate in the run: keep one only as an option when results vary by call.
- **Builds on:** the [seven-recording trial](https://github.com/pomodorozhong/meeting-recap/blob/c714e05/docs/experiments/2026-11-01-synthetic-collection.md) in draft PR #31, which is **not on `main`**. It developed the split on one recording, `stocktake`, and said the result needed another sparse recording to confirm it. It also reported the same text counts on the same silent recording and tried an all-zero rule. The same rule is in [`collection_followup.py`](../../experiments/synthetic-call/collection_followup.py) on `main`.

## Plan

- **Input:** all 17 mono recordings in the collection at `4c8c2f0`, checked against [committed hashes](../../experiments/synthetic-call/reference/collection-sha256.json). Sixteen are speech and one is 12 seconds of digital zeros. Four of the speech recordings have a pause of at least five seconds of exact zeros.
- **Assumptions:** one M2 Pro with 16 GB, one model process at a time. The reference is the generated script, not a listener's judgment, so nobody graded these results by ear. Each recognizer is told the script's language, and the silent recording is decoded as Mandarin. Word timestamps are on, and earlier text isn't fed back to the recognizer as a prompt.

| Run ID | Model and pinned version | Settings |
| --- | --- | --- |
| `whisper`, `turbo`, `breeze` | Same as the three rows below | Whole file, from the `decode` step |
| `split/whisper` | Full Whisper (`whisper-large-v3-mlx`) `49e6aa28` | Split wherever at least five seconds of samples are exactly zero, keeping 250 ms of context at each cut |
| `split/turbo` | Turbo (`whisper-large-v3-turbo-q4`) `660c343b` | Same |
| `split/breeze` | Breeze (`Breeze-ASR-25-mlx`) `172151e3` | Same |
| `silence/pipeline` | Full Whisper through the pipeline | `recap.py run --language zh`, whose default diarizer is Sortformer |
| `onboarding/pause-pipeline` | Full Whisper through the pipeline | `recap.py run --diarizer who --split-digital-pauses --no-summary` |

A recording without such a pause isn't decoded again: its split result is its whole-file result.

## Results

An **edit** is one inserted, deleted or substituted unit between the script and the recognizer's text. In English the unit is a word. In Mandarin it's a character, after converting to Simplified and keeping only letters and digits, so an English term in a Mandarin script counts letter by letter. Lower is better. "Whole" decodes the entire recording at once, and "split" decodes the speech on each side of the pause separately.

| Recording with a long digital pause | Full Whisper edits, whole → split | Turbo edits, whole → split | Breeze edits, whole → split |
| --- | ---: | ---: | ---: |
| `stocktake` (Mandarin, 116 characters, about 18 s pause) | 48 → 18 | 48 → 21 | 17 → 25 |
| `onboarding` (Mandarin, 305 characters, about 12 s pause) | 91 → 11 | 25 → 20 | 18 → 21 |
| `english-audit` (English, 495 words, about 8 s pause) | 16 → 16 | 12 → 12 | 16 → 52 |
| `english-training` (English, 526 words, about 8 s pause) | 14 → 11 | 11 → 11 | 19 → 28 |

Full Whisper and Turbo improved or tied on every row, and Breeze got worse on every row. Most of full Whisper's gain comes from recordings whose failure was already known. `stocktake` is byte-identical to the seven-recording trial's recording and gave the same counts. For `onboarding`, the [collection's README](../../experiments/synthetic-call/README.md#seventeen-recording-collection) already recorded that a full Whisper decode inserted unrelated text around the pause and omitted some following turns. On the two English recordings, for which the sources checked record no earlier failure, full Whisper tied once and saved three edits once.

Character error rate (CER) and word error rate (WER) divide total edits by the script's length in that unit. The totals below cover the 14 independent scripts: eight Mandarin (3,095 characters) and six English (3,028 words). They leave out two remixes that repeat other scripts' text. The other 12 speech recordings have no long pause, so only the four above can move these totals.

| Recognizer | Mandarin CER, whole → split | Mandarin edits | English WER, whole → split | English edits |
| --- | ---: | ---: | ---: | ---: |
| Full Whisper | 9.98% → 6.43% | 309 → 199 | 2.18% → 2.08% | 66 → 63 |
| Turbo | 7.59% → 6.56% | 235 → 203 | 1.98% → 1.98% | 60 → 60 |
| Breeze | 12.08% → 12.44% | 374 → 385 | 7.43% → 8.92% | 225 → 270 |

After the split, full Whisper and Turbo are close: full Whisper has four fewer Mandarin edits and three more English edits.

**Why the split helps isn't established.** Word positions don't point to text invented inside the pause: counting word midpoints inside the scripted pause, whole-file full Whisper placed none on `stocktake` or `onboarding`, its two largest counts, and split full Whisper placed one on each. A midpoint inside a pause can also be a timestamp error. Its whole-file text was shorter than the script on those two recordings (100 of 116 and 251 of 305 characters), which points toward missing speech, but the results file doesn't separate insertions from deletions. Breeze's whole-file count on `english-training` is missing because one segment has text but no word timestamps. Its edit count there is still valid.

**Silent input.** The reference for the 12-second silent recording is empty, so any output is invented. Decoded twice each, full Whisper returned 20 characters and Turbo 35, with the same text both times after that conversion, and Breeze returned nothing. Who and Sortformer, the two diarizers (which label who spoke when), each reported no speakers. The pipeline's check applies only to a nonempty converted WAV whose samples are all exactly zero. With it in place, the pipeline returned zero transcript turns and zero recap items in 6.69 s, and it marked recognition and the recap as skipped. It still checked and ran the diarizer. That result comes from this one file, so it shows only that the check works on this input. The check's code is the same for every recognizer, but only full Whisper's path was run.

**Pause option through the pipeline.** The acceptance check required the same error count as the experiment on `onboarding`, timestamps relative to the original recording, and a rendered transcript. On that recording, the only one checked this way, the command matched the experiment's split at 11 edits. The two speech spans and all 274 recognized words and their times also matched, including 105 words after the pause. It rendered 17 transcript lines in 21.45 s. These figures aren't in the results file. They are recorded in the earlier combined write-up, and [PR #36](https://github.com/pomodorozhong/meeting-recap/pull/36) repeats the word count. This shows that the pipeline reproduces the experiment. It isn't new evidence that the split helps. No English recording went through the pipeline with this flag.

**Limits.**

- All the pauses here were generated as exact zeros. A pause with room noise doesn't contain zeros, so this says nothing about it, and the rule isn't a voice activity detector.
- The pipeline checks the converted WAV, so a real mute counts only if its samples are still exactly zero after conversion. No real recording was tested.
- The evidence for the split is four recordings, two of them with known failures. Unit tests cover a quiet nonzero signal: it isn't treated as silent or cut, using mocked recognition.

## Runtime and memory

Measured with `/usr/bin/time -l`, one model process at a time, on the M2 Pro with 16 GB and the desktop in normal use. These are totals across the four recordings in the first table.

| Recognizer | Whole-file time | Split time | Largest whole-file peak | Largest split peak |
| --- | ---: | ---: | ---: | ---: |
| Full Whisper | 84 s | 120 s | 7.80 GB | 6.59 GB |
| Turbo | 48 s | 54 s | 3.33 GB | 2.63 GB |
| Breeze | 148 s | 154 s | 12.92 GB | 9.00 GB |

The whole-file runs used one process per recording and the split runs used one per chunk, so the split loaded each model twice as often. Peak is the memory footprint macOS reports, which [doesn't fully count Metal buffers](../../experiments/pipelines/whisper-sortformer/README.md). A two-job Swift compile overlapped part of the early timing of `english-audit` and the silent recording. The record doesn't say whether it touched the 6.69 s pipeline run. The pause option's 21.45 s reuses one loaded model and includes diarization and rendering, so it can't be compared with these totals.

## Decision

Skip recognition and the recap when every converted sample is exactly zero. This needs no flag.

Offer the split as `--split-digital-pauses` with full Whisper only, the pipeline's default recognizer. Pass it when a recording has digitally muted or silenced stretches. The pipeline has no command that reports this before a run, and it refuses the flag with `--asr turbo-q4`. Afterward, `asr.json` shows what happened: more than one entry in `spans_samples` means the recording was split. From the code, a recording with no five-second run of zeros decodes as a single span as usual, but this experiment ran no such recording through the flag.

The combined write-up's reason for offering it is that full Whisper improved or tied on all four recordings without its total rising in either language. This choice is cautious. The results don't favor full Whisper over Turbo: Turbo also didn't regress in either language, and the two end up close. Turbo is excluded because its version was never put through the pipeline's acceptance check, and the record doesn't say why only full Whisper was. Breeze got worse in both languages, and it isn't one of the pipeline's recognizers. The flag is off by default, which fits the plan's rule for results that vary by call. See decision 14 in [`decisions.md`](../decisions.md).

## Open questions

- Does the split help on real recordings with digital mutes? Nothing here tests that.
- Does the flag behave the same on an English recording through the pipeline, or with Turbo? Neither was run.
- Why does the split help full Whisper so much on `onboarding` and hurt Breeze so much on `english-audit`?
- Does any rule help with pauses that have room noise? No voice activity detection was evaluated.

## Where this ran

- **Code:** the collection is the one merged in #32 (`4c8c2f0`). The runs used development commits based on it, which the record doesn't name and which are **not on `main`**, before silence handling and `--split-digital-pauses` merged in #36. So the results file's numbers, including 6.69 s, come from those commits. PR #36 reports that on its pipeline code, the silent recording (with Who, not Sortformer) was skipped as expected, and that all 274 `onboarding` words and times matched the saved experiment output.
- **Models and weights:** the revisions in the plan. Full Whisper and Turbo are also pinned in [`pins.py`](../../experiments/pipelines/whisper-sortformer/pins.py), and Breeze in `collection_followup.py`. Text normalization used `transformers` 5.22.0 and `opencc-python-reimplemented` 0.1.7.
- **Machine:** one M2 Pro with 16 GB, one model process at a time. The macOS version isn't recorded.
- **Kept outside the repository:** raw audio and model outputs, under benchmark ID `expanded-pipeline-20261102`. The results file has counts and digests only. The same run's recognizer and diarizer comparisons are in [the recognition summary](2026-11-02-synthetic-collection-recognition.md) and [the speakers summary](2026-11-02-synthetic-collection-speakers.md).
