# Handoff

## In progress



### feat/app-recorder-prototype

- Task: a macOS app prototype for iterating the design (decision 17). It records for real; the transcript and recap are invented samples, and nothing is connected to the pipeline. It advances #28 and closes nothing, so the branch is unlinked.
- PR: opened from this branch against `main` and awaiting review; the number is in the PR itself. Code checkpoint: `44c2eb5`, branched from `main` at `ed23701`; `main` has since gained #72, which touches no `app/` files.
- State: `app/` holds a SwiftPM package (a `RecorderCore` library and the `MeetingRecap` SwiftUI app) with a collapsible recordings list, "New meeting" setup (microphone and call-app pickers), a live recorder, and Audio, Timeline and Recap tabs. The Timeline shows speech and screenshots in time order under an overview strip. Two sample meetings fill the list; their screenshots are drawn placeholders, and the app doesn't capture screenshots. Screenshot capture is planned in #73.
- Verification: `app/scripts/bundle.sh --test` passes 13 tests (generated audio only). Screenshots confirm the sample Audio, Timeline and Recap tabs, the setup screen, the full-width Start button and the recap spacing. Not exercised: a real recording from the app, the permission prompts, recording from one app, live waveforms, playback of a real recording, and clicks on the Choose menu, check bar, citation jumps, strip jumps, checkboxes, Copy, Save and sidebar collapse.
- Next action: the user records a real call to try the untested parts, then gives more design feedback. Open design question: should recap items cite screenshots as well as lines.

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

### feat/turbo-pause-check-run

- Task: #46, run Turbo through the pause option's acceptance check. The branch isn't linked to #46 (the linked branch `feat/turbo-pause-check` is checked out in another worktree), so the PR body must say `Closes #46`.
- PR: none yet. Code checkpoint: `main` at `ed23701` plus the commits on this branch; nothing pushed.
- State: the plan and `turbo_pause_check.py` were committed before the run; the code change allows `--split-digital-pauses` with Turbo; the run passed all four checks (same spans, 273 words and times, 20 edits, transcript written); the summary is complete and decision 16 is added.
- Verification: pipeline tests pass (35); the run used the dataset's converted `onboarding` audio, since the original `call.wav` isn't on this machine; a privacy scan of the diff passes.
- Next action: ask the user to approve pushing this branch and opening the PR with the `open-pr` skill. The old local branch `feat/turbo-pause-check` (and its remote copy) holds only the handoff and a merge of `main`; after the PR, delete or retire it.

### feat/recap-stage-entry-point

- Task: #28 (advances it; branch not linked, since the PR won't resolve the issue). PR: [#77](https://github.com/pomodorozhong/meeting-recap/pull/77), open and awaiting review.
- Code checkpoint: `2cf8232` (the PR tip is a later `docs:` commit), built on `main`. Adds `experiments/recap-stage/run.py` (Stage A variants A0, A0-noise, A1, A2, A3), its uv project and `tests/experiments/test_recap_stage.py`; the plan's Reproduce section now describes it.
- Verified: `tests/experiments` discovery, 21 tests, pass (fake model). Real model: all five variants ran on a 7-line made-up transcript with the pinned Qwen3.5 9B (A0 26 s, A0-noise 20 s, A1 24 s, A2 317 s, A3 37 s; peak MLX 5.9 to 6.0 GB; every cited timestamp matched a line). A1's not-run path and long-call chunk-and-merge were not exercised with the real model.
- Mechanical pass on all 16 real calls is done and summarized in the plan's Results (committed locally on this branch, not yet pushed): most recaps are not valid notes, because replies hit the 4,096-token output cap, mostly at the merge step; A1 gives valid notes on 10 of 12 runs but cannot run on the 4 longest calls; A2 never finishes. Private outputs are in a stage-a folder outside the checkout. The plan's pass rule needs a decision on this before keys are written.
- Next: wait for review of #77. Then the recap cut-off fix ranked first in [docs/next-steps.md](docs/next-steps.md), registered as a dated plan change before it runs; A4 models and answer keys follow it.
- Still open in the plan before any real-call run: the screening score method and prompt (decision 1), A4's candidate models and pins, and the owner's answer keys.

## Ranked work

1. Follow [docs/next-steps.md](docs/next-steps.md), the effort and impact ranking of 2026-11-13. Its top items: review and merge #77, #81 and #82; decide P-02; then fix the recap cut-off (most real-call recaps hit the 4,096-token output cap) before any grading or model comparison. The items below are the full backlog it ranks.
2. #28 Run the private-recording pipeline review. The plan is on `main`; the Stage A entry point is in #77, awaiting review. Next: fix the recap cut-off, then A1's length limit and pinned A4 models, then the project owner's answer keys.
3. #18 Complete the two-track listening review, freeze its reference, evaluate both runs and finish the public summary; current turn counts remain provisional.
4. #11 Compare real-call transcript accuracy; the synthetic evidence is on `main`.
5. #1 Finish the user-confirmed long-call Who comparison; draft #25 remains open.
6. #47 Grade a recap on a long meeting; can fold into #28's Stage A grading.
7. #48 Separate Turbo from Who in the recap comparison; in #81, awaiting review.
8. #50 Test `--keep-asr-segments` with full Whisper and Sortformer; in #82, awaiting review.
9. #57 Add synthetic noisy calls to the test collection.
10. #53 Warn when a recording's language looks wrong for `--language`.
11. #54 Reconcile the recognizer memory figures across reports.
12. #55 Separate temperature from word timestamps in the recognition baseline.
13. #4 Run each remaining runner and the review skill end to end on the synthetic collection, and record the results.
14. Revisit draft #31, `codex/action-grounding-sequence` and the deferred baseline and recap-accuracy branches. Keep `c714e05` and `d182e52` reachable: the merged summaries link to them, on #31's branch and `codex/expanded-call-benchmark`. The latter's commits also show when each criterion's text was registered.
15. #9 Choose a license.
16. #7 Decide where private experiment data is backed up.
17. #5 Extend reproducibility instructions to the remaining public summaries.
18. #3 Migrate the earlier experiment results into the private review dataset.
19. Remaining runner follow-ups: external model-cache verification, the no-VAD variant and completion checks outside the HushScribe export fix.
20. #73 Design how screenshots are captured and used in the recap.

## Pending

- P-02 — Decide draft #31: rewrite it against the 17-recording collection, or close it and keep `c714e05` reachable, for example with a tag. The action comparison left out of #37's split belongs with this decision. It blocks #31's wording pass and `codex/action-grounding-sequence`. Checked 2026-11-03: it conflicts with `main` in 10 files and its pipeline options and runners have merged in other forms. What only it holds is the action-recovery work. Recommended: tag `c714e05`, close it, and file an issue for action recovery. On 2026-11-04 the user asked what the tag is for: the recognition, speakers, silence and recaps summaries on `main` link to `c714e05`, which only #31's branch holds, and only the action-recovery work is unique to #31. Still awaiting the decision on whether to keep action recovery.
