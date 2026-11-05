# 2026-11-05: Turbo through the pause option's acceptance check

**Status:** planned

**Outcome:** pending

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/synthetic-call/collection_setup.sh`, then `recap.py setup --asr all --who` from [the pipeline's README](../../experiments/pipelines/whisper-sortformer/README.md) |
| Run everything | `uv run --project experiments/synthetic-call experiments/synthetic-call/turbo_pause_check.py "$FIXTURES" "$RESULTS" "$SPLIT_TURBO"` |
| Check saved results without models | not possible: the check compares a new pipeline run with a saved split output |

- **It needs:** `FIXTURES`, the verified 17-recording collection built by [`collection.py`](../../experiments/synthetic-call/README.md#seventeen-recording-collection); `RESULTS`, a new absolute path outside Git; and `SPLIT_TURBO`, the `onboarding/split/turbo.json` file that the `split` step of [the digital silence experiment](2026-11-02-synthetic-collection-silence.md) wrote, with its `spans.json` beside it. The script exits with an error if any of them is missing.
- **It writes:** the pipeline's output folder, and `RESULTS/check.json` with each measured value and whether each check passed.
- **Takes about:** not measured yet.
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

Pending.

## Runtime and memory

Pending.

## Decision

Pending.

## Open questions

- A pass covers one Mandarin recording. It says nothing about an English recording, or about a recording without a long pause.

## Where this ran

Pending.
