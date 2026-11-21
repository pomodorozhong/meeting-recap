# Next steps, ranked by effort and impact

Written 2026-11-13 from [HANDOFF.md](../HANDOFF.md), [decisions](decisions.md), the [experiment summaries](experiments/README.md) and the open issues and PRs on GitHub. It is a snapshot: re-rank it when a step finishes or a result changes the picture.

## Where the project stands

**Goal:** meeting notes (decisions and action items with owners) produced locally on an M2 Pro with 16 GB, covering the 22 behaviors in the feature catalogue ([status](README.md)).

**Settled:** the transcript side. Full Whisper with the declared language, Sortformer and per-word label attachment is the default; Turbo and Who are the fast options (decisions 12 to 16). The app records for real but shows a mock recap (decision 17).

**Not settled:** the recap. In the [mechanical pass on 16 real calls](experiments/2026-11-04-recap-stage-real-calls.md#mechanical-pass-on-all-16-calls-exploratory-2026-11-06-to-07), the shipped recap gave valid notes on only 3 calls, the three shortest. Every call of 37 minutes or more failed, because a reply reaches the 4,096-token output cap, mostly in the merge step.

| Variant | Valid notes | Problem |
| --- | --- | --- |
| A0 baseline | 3 of 16 | Cut off at the output cap |
| A0-noise | 1 of 16 | Same, so it gives no usable noise floor |
| A1 one pass | 10 of 12 run | Can't run the 4 longest calls; peaks at 9.6 GB |
| A2 thinking on | 0 of 16 | Runs out of tokens while still reasoning |
| A3 rewritten prompt | 2 of 16 | Cut off at the output cap |

So the planned graded comparison (answer keys, blind grading, Stage B) can't start yet: there are almost no valid notes to grade.

## Housekeeping first

These are cheap and unblock other work.

| Rank | Step | Effort | Impact |
| --- | --- | --- | --- |
| 1 | Review and merge [#77](https://github.com/pomodorozhong/meeting-recap/pull/77) (recap-stage entry point), [#81](https://github.com/pomodorozhong/meeting-recap/pull/81) (recaps from four recognizer and diarizer pairs) and [#82](https://github.com/pomodorozhong/meeting-recap/pull/82) (per-segment lines with full Whisper and Sortformer) | Low | High: three finished pieces are waiting on review |
| 2 | Decide P-02 in [HANDOFF.md](../HANDOFF.md#pending) (draft [#31](https://github.com/pomodorozhong/meeting-recap/pull/31)). Recommended: tag `c714e05`, close #31, and let [#75](https://github.com/pomodorozhong/meeting-recap/issues/75) carry action recovery | Low | Medium: unblocks two stale branches |
| 3 | Record one real two-person call with the app, wearing headphones | Low | Medium: exercises the app's untested parts and gives [#18](https://github.com/pomodorozhong/meeting-recap/issues/18) its two-track call |

## Experiments

| Rank | Experiment | Effort | Impact | Notes |
| --- | --- | --- | --- | --- |
| 1 | **Fix the recap cut-off**, judged mechanically on the 16 saved transcripts. Candidates: a higher output cap; merging chunk notes in code instead of asking the model to repeat them; a tighter limit on items per chunk | Low to medium: no listening, transcripts already saved, a few hours of machine time | Highest: the shipped pipeline fails on calls of normal length, and everything below waits on it | Needs a dated change in the recap-stage plan, committed before the first run (decision 11). Proposed pass rule: valid notes on all 16 calls, every cited timestamp matching a transcript line, and peak MLX memory under 9 GB |
| 2 | **Long calls in one pass (A1) and other recap models (A4).** Find how long a call fits in one pass, and pin two or three MLX models under the memory limit | Medium | High: A1 is the only variant that mostly works | Run after 1, so models are compared on a recap that completes. Also settle whether the 9 GB limit stands, since A1 already peaked at 9.6 GB. Which MLX models fit hasn't been looked up yet |
| 3 | **Answer keys for 6 calls**, at least two over 60 minutes | High, and all of it the project owner's listening | High: nothing can be called correct without them | Proposed plan change: choose the 6 calls by length now and skip the screening against Amie, whose scoring method isn't designed ([#61](https://github.com/pomodorozhong/meeting-recap/issues/61), [#63](https://github.com/pomodorozhong/meeting-recap/issues/63), [#64](https://github.com/pomodorozhong/meeting-recap/issues/64)) |
| 4 | **Stage A graded, then Stage B** (the default against Turbo + Who and against Amie) | High | High: this is the decision the project is waiting for | Needs 1 to 3. It also answers [#47](https://github.com/pomodorozhong/meeting-recap/issues/47), which can fold into it |
| 5 | **Two-track speaker review** ([#18](https://github.com/pomodorozhong/meeting-recap/issues/18)) | Medium | Medium: a speaker reference without long listening sessions | Needs the recorded call from housekeeping step 3 |
| 6 | **Real-call transcript accuracy** ([#11](https://github.com/pomodorozhong/meeting-recap/issues/11)) | Medium to high: needs a hand-made reference | Low to medium: pipelines are now judged on the notes, not on transcript error | Defer |
| 7 | **Who on long calls** ([#1](https://github.com/pomodorozhong/meeting-recap/issues/1), draft [#25](https://github.com/pomodorozhong/meeting-recap/pull/25)) | Medium | Low: Stage B's Turbo + Who run covers the useful part | Defer, or close with draft #25 |
| 8 | Speaking indicator ([#71](https://github.com/pomodorozhong/meeting-recap/issues/71)), voice prints ([#76](https://github.com/pomodorozhong/meeting-recap/issues/76)), noisy synthetic calls ([#57](https://github.com/pomodorozhong/meeting-recap/issues/57)), LFM3-Audio ([#27](https://github.com/pomodorozhong/meeting-recap/issues/27)), Apple's on-device model ([#70](https://github.com/pomodorozhong/meeting-recap/issues/70)), oMLX ([#60](https://github.com/pomodorozhong/meeting-recap/issues/60)) | Medium to high each | Low for now: they tune parts that aren't the bottleneck | Defer until the recap works |

## Recommendation

Do the housekeeping, then experiment 1 before anything else. Until a recap completes on a call of normal length, grading, model comparison and Stage B have nothing to work on.
