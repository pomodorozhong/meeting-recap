# Handoff

## In progress

### fix/capture-safety

- Task: fix the recorder findings from a second code review (P1): it wrote into the current folder, the public checkout, when `MEETING_REVIEW_DATA` was unset; a trailing `--app` recorded all system audio; and write failures still printed "saved" and exited 0. No issue. Based on `main`, unlinked.
- PR: https://github.com/pomodorozhong/meeting-recap/pull/21 (open, base `main`, ready for review; closes nothing). Rebased onto `main` after #20 merged.
- Code checkpoint: see `git log`. `fix(capture)` changes `experiments/capture/record.swift` and its README.
- Verification: `swiftc -typecheck` passes with no warnings. A built binary exits 2 before capturing for: no destination, `--app` or `--app --mic x` without a value, `--out` inside the checkout, `--out` through a symlink into it, `MEETING_REVIEW_DATA` inside it, and a folder that holds files. Not run: a live recording (needs capture permissions and a call), so the failure path is checked by reading only.
- Next action: review and merge PR #21; then record a short test call to check the normal path still prints `saved` and exits 0.

## Ranked work

1. #18 Use a two-person two-track call as its own speaker reference: recorder, decision 6, and `review.py tracks` merged in #19. Left: the user listens to session `check-two-track-call` (command in `docs/experiments/2026-10-30-two-track-call.md`), then freeze `ref-check-two-track-call`, run `eval-check-two-track-call` on both runs, write the private report, and finish the summary (Sortformer's 528/629 turns is provisional until then)
2. #4 Add a shareable synthetic test recording (the call merged in #17; the remaining runners still need to run on it)
3. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
4. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (blocks choosing the pipeline's ASR model)
5. #9 Choose a license
6. #7 Decide where private experiment data is backed up
7. #5 Add a Reproduce section to public experiment summaries
8. #3 Migrate the 2026-10-24 experiment results into the private review dataset
9. Remaining code review findings R-08–R-10 and R-13 in `experiments/` runners (no issue yet): model pinning, the no-VAD variant, runner completion checks, sweep output reuse. The skill findings merged in #20; the follow-ups are in #22
10. Build the minimal pipeline for saved recordings in `experiments/pipelines/`: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet)

## Pending

None.
