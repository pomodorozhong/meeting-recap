# Handoff

## In progress

### fix/skill-review-findings

- Task: fix the skill-side code review findings R-01–R-04, R-07, R-11, R-12 and R-14 (no issue; the review report is private to the reviewing session). Based on `main` after #19, unlinked. R-05 and R-06 were fixed in #19; the runner findings R-08–R-10 and R-13 are a separate task.
- PR: https://github.com/pomodorozhong/meeting-recap/pull/20 (open, base `main`, ready for review; closes nothing). The user approved opening it.
- Code checkpoint: see `git log`. The first five `fix(skill)` commits cover the findings. Two more address a review of the PR: a failed attachment no longer deletes a racing caller's completed run, and every buffered zero-length word must be within `--max-gap` of the word it joins (`14a03af`); every dataset write checks its resolved destination folder, so a symlinked `runs/` can't carry writes into a checkout or out of the dataset (`8270109`). A second review found the answer log itself could be a symlink: `append_event` now checks `events.jsonl` and `.lock` too.
- Verification: 95 skill tests pass, and each commit passes on its own. Each new regression test was run before its fix and failed. The diff was scanned for names and private paths. Not run: `dataset.py validate` on the real dataset.
- Compatibility: evaluations written before this branch, such as `eval-two-track-call`, have no digest; `validate` checks their links and lists them under `unsealed_evaluations`. Rerun `evaluate.py` under a new ID to seal one.
- Next action: the reviewer re-reviews PR #20; its body describes every fix and the 95-test result.

## Ranked work

1. #18 Use a two-person two-track call as its own speaker reference: recorder, decision 6, and `review.py tracks` merged in #19. Left: the user listens to session `check-two-track-call` (command in `docs/experiments/2026-10-30-two-track-call.md`), then freeze `ref-check-two-track-call`, run `eval-check-two-track-call` on both runs, write the private report, and finish the summary (Sortformer's 528/629 turns is provisional until then)
2. #4 Add a shareable synthetic test recording (the call merged in #17; the remaining runners still need to run on it)
3. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
4. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (blocks choosing the pipeline's ASR model)
5. #9 Choose a license
6. #7 Decide where private experiment data is backed up
7. #5 Add a Reproduce section to public experiment summaries
8. #3 Migrate the 2026-10-24 experiment results into the private review dataset
9. Remaining code review findings R-08–R-10 and R-13 in `experiments/` runners (no issue yet): model pinning, the no-VAD variant, runner completion checks, sweep output reuse. The skill findings are on `fix/skill-review-findings`
10. Build the minimal pipeline for saved recordings in `experiments/pipelines/`: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet)

## Pending

None.
