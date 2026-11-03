# 2026-11-02: digital silence on the 17-recording synthetic collection

**Status:** complete

**Outcome:** Splitting at five-second digital pauses helped full Whisper and Turbo and made Breeze worse in both languages. Only full Whisper's version was accepted and checked through the pipeline, so it's the one offered. Recognizers can invent text on digital silence, so an all-zero recording now skips recognition and the recap. Both rules apply to exact digital zeros only, not to quiet rooms or audible silence.

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/synthetic-call/collection_setup.sh` |
| Run everything | `experiments/synthetic-call/collection_run.sh "$FIXTURES" "$RESULTS"` |
| Rerun this summary's steps | `experiments/synthetic-call/collection_run.sh "$FIXTURES" "$RESULTS" --step split`, then `--step replays` |
| Check saved results without models | `uv run --project experiments/synthetic-call experiments/synthetic-call/collection_scores.py "$FIXTURES" "$RESULTS" > scores.json` |

- **It needs:** `FIXTURES`, the verified collection built by [`collection.py`](../../experiments/synthetic-call/README.md#seventeen-recording-collection), and `RESULTS`, a new absolute path outside Git. Scoring also reuses the `decode` step's whole-file outputs.
- **It writes:** every model output under `RESULTS`, with the measurements in `RESULTS/scores.json`. This is one run shared by [several summaries](../../experiments/synthetic-call/README.md#compare-the-pipeline-on-this-collection), so the scorer needs every step's outputs. [The saved measurements](2026-11-02-synthetic-collection-results.json) are the committed copy.
- **Takes about:** 5.5 minutes for `split`, in the saved timings; `replays` wasn't timed. The whole run takes about 54 minutes, plus the untimed `turns` and `replays` steps.
- **By hand:** nothing for this summary.
- **Expect to differ:** timings on any rerun, and possibly model text on another machine. The scorer recalculates the measurements from saved outputs, so it should match the committed file byte for byte.

## Question

Does decoding around long digital pauses reduce recognition errors, in either language? What should the pipeline do when a whole recording is digital zeros?

- **Decision it informs:** whether to offer the split, for which recognizers, and whether silent input skips recognition.
- **Expected result:** none stated for the size of the effect. The trial's splitter stays experimental unless neither language regresses. Internal pause errors are kept separate from pure silence.
- **Builds on:** a [seven-recording trial](https://github.com/pomodorozhong/meeting-recap/blob/c714e05/docs/experiments/2026-11-01-synthetic-collection.md) in draft PR #31, which is **not on `main`**. Its `silence_split.py` at `c714e05` defines the rule.

## Plan

- **Input:** all 17 hash-verified mono fixtures in the collection at `4c8c2f0`. Four speech recordings have a qualifying pause.
- **Assumptions:** one M2 Pro with 16 GB, serial local inference. Generated text is the known intended speech, not a listener judgment.

| Run ID | Model and pinned version | Settings |
| --- | --- | --- |
| `split/whisper` | Full Whisper `49e6aa28` | Five-second exact-zero split with 250 ms context, language-matched |
| `split/turbo` | Turbo Q4 `660c343b` | Same |
| `split/breeze` | Breeze `172151e3` | Same |

Unchanged audio reuses the unsplit result.

### Changes to the plan

The criteria were fixed before the runs they govern. Their wording was later edited to read against `main`; no threshold or rule changed.

Two checks were added after earlier results, so they are exploratory rather than part of the first plan:

- **Entirely silent input:** added after full Whisper emitted the same 20 alphanumeric characters twice on 12 seconds of digital zero, and Turbo emitted 35 twice. Only a nonempty converted WAV whose samples are *all exactly zero* may skip ASR and produce an empty transcript and a no-speech recap without the LLM. Ordinary nonzero speech and internal pauses stay on the normal path, and the regression check includes a quiet nonzero sample.
- **Full-Whisper pause option:** full Whisper improved or tied on each of the four eligible cases, with no regression in either language aggregate, so the rule was offered as an explicit option for this model only. Before acceptance, the pipeline command had to give the same normalized error count on onboarding as the benchmark split, with source-relative timestamps and a rendered transcript.

On 2026-11-03, after the runs, this summary was split out of one write-up covering every question, so that each question has its own summary and decision. No result changed. Nothing was rerun for the split.

## Results

| Speech with a qualifying pause | Full Whisper edits, whole → split | Turbo edits | Breeze edits |
| --- | ---: | ---: | ---: |
| Stocktake (Mandarin; same audio as the trial) | 48 → 18 | 48 → 21 | 17 → 25 |
| Onboarding (Mandarin) | 91 → 11 | 25 → 20 | 18 → 21 |
| Audit (English) | 16 → 16 | 12 → 12 | 16 → 52 |
| Training (English) | 14 → 11 | 11 → 11 | 19 → 28 |

The other 12 speech WAVs pass through without a change. Across the 14 independent scripts:

| Recognizer | Mandarin CER, whole → split | English WER, whole → split |
| --- | ---: | ---: |
| Full Whisper | 9.98% → 6.43% | 2.18% → 2.08% |
| Turbo Q4 | 7.59% → 6.56% | 1.98% → 1.98% |
| Breeze | 12.08% → 12.44% | 7.43% → 8.92% |

One whole-file Breeze gap diagnostic lacks word timestamps and is unavailable, not zero. The text remains scoreable.

**Silent input.** On the silence WAV shared with the trial, full Whisper, Turbo and Breeze again emitted 20 / 35 / 0 normalized characters. With the check, the pipeline returned zero transcript turns and zero recap items in 6.69 s, with ASR and summary marked as skipped. It still checked and ran the selected diarizer.

**Pause option through the pipeline.** The full-Whisper command with `--split-digital-pauses --diarizer who --no-summary` matched the onboarding split result: **11 edits instead of 91**. The two source spans and all 274 recognized words and their start and end times matched the experiment, including 105 words after the pause. It rendered 17 transcript lines in 21.45 s end to end.

**Limits.** This is a five-second digital-zero rule, not evidence about splitting acoustic pauses, and not a voice activity detector. The check says nothing about room noise or audible silence.

## Runtime and memory

One inference process ran at a time on the M2 Pro with 16 GB, measured with `/usr/bin/time -l`, with the desktop in normal use. Split decoding took 120 s for full Whisper, 54 s for Turbo and 154 s for Breeze in total across the qualifying recordings, each chunk in its own process. The pipeline option reuses a loaded model within one command, so its 21.45 s isn't comparable to those totals.

## Decision

Skip recognition and the recap on entirely zero audio. Offer the exact-zero split as an option for digitally edited recordings, with full Whisper only. It made Breeze worse in both languages. It also improved or tied Turbo on every case, but Turbo's version wasn't put through the pipeline's acceptance check, so `--split-digital-pauses` stays limited to full Whisper. See decision 14.

## Open questions

Whether any rule helps on real-room pauses is untested here, and so is the split with Turbo through the pipeline's command. No voice activity detection was evaluated.

## Where this ran

- **Code:** the collection is the one merged in #32 (`4c8c2f0`). The runs used development commits based on it, before silence handling and `--split-digital-pauses` merged in #36. The development commits are not on `main`. Replaying the silence and split commands on the pipeline code in `main` gave the results above.
- **Models and weights:** the revisions in the plan, and in [`pins.py`](../../experiments/pipelines/whisper-sortformer/pins.py).
- **Machine:** one M2 Pro with 16 GB, one inference process at a time.
- **Kept outside the repository:** raw calls and predictions, under benchmark ID `expanded-pipeline-20261102`. Public results contain counts and digests only.
