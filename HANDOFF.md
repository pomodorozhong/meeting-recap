# Handoff

## In progress



### feat/app-meeting-tab

- Task: the app prototype's next design step ([#74](https://github.com/pomodorozhong/meeting-recap/pull/74) merged the first one): one Meeting tab in place of Audio and Timeline, with a player that stays on screen. It advances #28 and [#73](https://github.com/pomodorozhong/meeting-recap/issues/73) and closes nothing, so the branch is unlinked.
- PR: none yet; awaiting the user's approval to push and open one. Code checkpoint: `main` at `4f26736` plus the commits on this branch.
- State: tabs are Meeting and Recap. The sticky player holds play, both waveforms and a strip of turns and screenshot marks, with one playhead; clicking any of them, or a line or screenshot, moves it and scrolls the feed. A sample's playhead is simulated because it has no audio. A real recording shows the player and its files; its transcript and screenshots aren't connected. The app doesn't capture screenshots (#73).
- Verification: `app/scripts/bundle.sh --test` passes 13 tests (generated audio only). A screenshot of the sample Meeting tab with the playhead at 1:10 shows the layout. Not exercised: clicking and dragging the player, line and screenshot seeks, the playing highlight and auto-scroll, Play on a sample, that the player stays put while the feed scrolls, and everything on a real recording (permission prompts, one-app capture, live waveforms, playback).
- Next action: the user tries it and gives design feedback. Open question: should recap items cite screenshots as well as lines.

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

## Ranked work

1. #46 Turbo pause check: run and written up; waiting for the PR (on `feat/turbo-pause-check-run`).
2. #28 Run the private-recording pipeline review. The public plan is on `docs/recap-stage-plan`; next the entry point, pinned recap models and the project owner's answer keys.
3. #18 Complete the two-track listening review, freeze its reference, evaluate both runs and finish the public summary; current turn counts remain provisional.
4. #11 Compare real-call transcript accuracy; the synthetic evidence is on `main`.
5. #1 Finish the user-confirmed long-call Who comparison; draft #25 remains open.
6. #47 Grade a recap on a long meeting.
7. #49 Score label attachment on Turbo's text. Should need no new model runs.
8. #51 Add the `replays` results to the scorer and results file.
9. #52 Run the collection entry point end to end on a fresh folder. `collection_run.sh` hasn't been run whole from a new folder.
10. #57 Add synthetic noisy calls to the test collection.
11. #53 Warn when a recording's language looks wrong for `--language`.
12. #54 Reconcile the recognizer memory figures across reports.
13. #55 Separate temperature from word timestamps in the recognition baseline.
14. #48 Separate Turbo from Who in the recap comparison.
15. #50 Test `--keep-asr-segments` with full Whisper and Sortformer.
17. #4 Run each remaining runner and the review skill end to end on the synthetic collection, and record the results.
18. Revisit draft #31, `codex/action-grounding-sequence` and the deferred baseline and recap-accuracy branches. Keep `c714e05` and `d182e52` reachable: the merged summaries link to them, on #31's branch and `codex/expanded-call-benchmark`. The latter's commits also show when each criterion's text was registered.
19. #9 Choose a license.
20. #7 Decide where private experiment data is backed up.
21. #5 Extend reproducibility instructions to the remaining public summaries.
22. #3 Migrate the earlier experiment results into the private review dataset.
23. Remaining runner follow-ups: external model-cache verification, the no-VAD variant and completion checks outside the HushScribe export fix.
24. #73 Design how screenshots are captured and used in the recap (new, not yet ranked against the rest).

## Pending

- P-02 — Decide draft #31: rewrite it against the 17-recording collection, or close it and keep `c714e05` reachable, for example with a tag. The action comparison left out of #37's split belongs with this decision. It blocks #31's wording pass and `codex/action-grounding-sequence`. Checked 2026-11-03: it conflicts with `main` in 10 files and its pipeline options and runners have merged in other forms. What only it holds is the action-recovery work. Recommended: tag `c714e05`, close it, and file an issue for action recovery. On 2026-11-04 the user asked what the tag is for: the recognition, speakers, silence and recaps summaries on `main` link to `c714e05`, which only #31's branch holds, and only the action-recovery work is unique to #31. Still awaiting the decision on whether to keep action recovery.
