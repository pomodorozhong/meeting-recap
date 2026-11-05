# 2026-11-05: Turbo through the pause option's acceptance check

**Status:** complete

**Outcome:** With the pause option allowed for Turbo, the pipeline reproduced Turbo's earlier split result on the generated `onboarding` call: the same two speech spans, the same 273 words with the same times, and 20 edits against the script. All four checks in the pass rule held, so the pipeline now accepts the option with Turbo. This covers one Mandarin recording and no real call.

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/synthetic-call/collection_setup.sh`, then `recap.py setup --asr all --who` from [the pipeline's README](../../experiments/pipelines/whisper-sortformer/README.md) |
| Run everything | `uv run --project experiments/synthetic-call experiments/synthetic-call/turbo_pause_check.py "$FIXTURES" "$RESULTS" "$SPLIT_TURBO"` |
| Check saved results without models | not possible: the check compares a new pipeline run with a saved split output |

- **It needs:** `FIXTURES`, the verified 17-recording collection built by [`collection.py`](../../experiments/synthetic-call/README.md#seventeen-recording-collection); `RESULTS`, a new absolute path outside Git; and `SPLIT_TURBO`, the `onboarding/split/turbo.json` file that the `split` step of [the digital silence experiment](2026-11-02-synthetic-collection-silence.md) wrote, with its `spans.json` beside it. The script exits with an error if any of them is missing.
- **It writes:** the pipeline's output folder, and `RESULTS/check.json` with each measured value and whether each check passed.
- **Takes about:** 34 s from command to verdict on the machine below, models already cached.
- **By hand:** none.
- **Expect to differ:** timings. Turbo decodes greedily, so its words should match the saved output exactly; a difference is itself a result.

## Question

Does the pipeline's `--split-digital-pauses` option, run with Turbo, reproduce the Turbo result from the digital silence experiment?

The option decodes the speech on each side of a stretch of at least five seconds of exact digital zeros, then restores the original timestamps. It is limited to full Whisper today. [Decision 14](../decisions.md) says why: only full Whisper's version was run through the pipeline's acceptance check, and the record doesn't say why Turbo's wasn't.

- **Decision it informs:** whether to offer the option with Turbo as well as full Whisper. A pass removes the only recorded difference between the two recognizers. A failure keeps the option full-Whisper-only.
- **Expected result:** a pass, because the pipeline calls the same splitting code with a different pinned model. No size of effect is expected, since this checks reproduction and not improvement.
- **Builds on:** [the digital silence experiment](2026-11-02-synthetic-collection-silence.md), which made the full Whisper check this one repeats.

## Plan

- **Input:** one generated Mandarin call with English terms, one mono track, about 12 seconds of exact digital zeros in the middle, and a script of 305 characters. It is `onboarding` in the 17-recording synthetic collection. No real recording is used.
- **Assumptions:** one M2 Pro with 16 GB and nothing else running; models already cached; the spoken language is the pipeline's default, Mandarin; Who is the diarizer, as in the full Whisper check.

| Run ID | Model and pinned version | Settings |
| --- | --- | --- |
| `onboarding/turbo-pause-pipeline` | Turbo (`whisper-large-v3-turbo-q4`) `660c343b` | `recap.py run --asr turbo-q4 --diarizer who --split-digital-pauses --no-summary` |

**Reference.** Turbo's split output from the digital silence experiment, `onboarding/split/turbo.json`. An **edit** is one inserted, deleted or substituted character between the script and the recognizer's text, after converting to Simplified and keeping only letters and digits (lower is better). That output has 20 edits.

**Pass rule, written before the first run.** All four must hold:

1. The run's `asr.json` lists the same two speech spans as the saved `spans.json`.
2. Its words, and each word's start and end time, match the saved split output word for word, within 1 ms. Words after the pause are in this comparison, so it checks that their times are measured from the start of the original recording.
3. The edit count against the script is 20.
4. The run writes a transcript, and at least one recognized word starts after the pause.

If any fails, the option stays full-Whisper-only and the failing check is reported.

**Code change.** The pipeline refuses the option with Turbo in `recap.py` and `asr_stage.py`, and a test expects that refusal. The change removes both refusals and turns the test into one that expects the run to be accepted. It is part of this branch so the check can run.

**Audio.** The original `call.wav` is not on the machine that runs this. The private dataset keeps the pipeline's converted 16 kHz mono copy of it, whose hash differs from the original's. If the run uses that copy, the summary says so and what was done to confirm the two decode alike.

### Changes to the plan

None.

## Results

| Check | Saved split output | Pipeline run | Pass |
| --- | --- | --- | --- |
| Speech spans, in samples at 16 kHz | 0–884,278 and 1,069,504–1,594,032 | the same two | yes |
| Recognized words | 273 | 273, each matching in text and in start and end time to within 1 ms | yes |
| Edits against the script (lower is better) | 20 | 20 | yes |
| Words starting after the pause | not counted | 105, so times after the pause are measured from the start of the recording | yes |
| Transcript | not applicable | 24 lines written | yes |

Full Whisper's earlier pipeline check found 274 words on this recording. The one-word difference is two models on one recording, not a comparison between them.

**Limits.**

- One generated Mandarin recording with one long pause. An English recording, a recording with no long pause, and a real recording with a digital mute were not run.
- The run used the pipeline's converted copy of the recording from the earlier experiment, not the original `call.wav`, which this machine doesn't have. The earlier pipeline run's converted audio has the same SHA-256 as the file used here, so the pipeline decoded the same samples both times. The reference text was rebuilt from the committed script, joining its turns the way the collection builder does, because the fixture's transcript file wasn't available. It gave the same 20 edits as the saved output, which also supports that the text is the same.
- A pass shows that the pipeline reproduces the experiment for Turbo. It isn't new evidence that the split helps; that evidence is in the digital silence experiment.

## Runtime and memory

Measured by the pipeline's own stage timers and `asr.json`, one model process at a time, on the machine below. The recognition stage took 29.8 s, of which the recognizer reported 10.6 s of decoding; the rest is loading the model. Peak MLX memory was 1.37 GB. Diarization with Who took 0.7 s. These figures are one run and weren't repeated.

## Decision

Offer `--split-digital-pauses` with Turbo as well as full Whisper, and remove the refusal. This follows from the pass: decision 14 excluded Turbo only because its version had not been through this check, and it now has. The choice is the same cautious one as decision 14. The option stays off by default, and the evidence is still one generated recording plus the four-recording experiment. Nothing here favors Turbo over full Whisper or the reverse. See decision 16 in [`decisions.md`](../decisions.md).

## Open questions

- A pass covers one Mandarin recording. It says nothing about an English recording, or about a recording without a long pause.

## Where this ran

- **Code:** the check script and the code change that allows the option with Turbo are on the branch of the PR that adds this summary, which isn't on `main` until it merges. The plan and script were committed before the run. The run used the commit that removes the refusal.
- **Models and weights:** Turbo `660c343b`, as in the plan. Who's int8 weights, checked by the pipeline against its pinned digest before the run.
- **Machine:** M2 Pro, 16 GB, macOS 26.6.2.
- **Kept outside the repository:** the generated recording's converted audio and the saved split outputs of the digital silence experiment.
