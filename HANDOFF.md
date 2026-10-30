# Handoff

## In progress

### fix/skill-review-followups

- Task: fix the new skill findings from a second code review: turns too short to score in known references (6), playback without a digest check (9), snapshots without `pyproject.toml`/`uv.lock` (12), transcripts without word timing in clip picking (14), track activity time drift (16), finishing from a stale tab (17), and edits lost during a save (18). No issue. Also carries a fix that missed #20's merge: a word or segment that is only special tokens makes no attached turn. Rebuilt onto `main` after #20 and #21 merged, unlinked.
- PR: https://github.com/pomodorozhong/meeting-recap/pull/22 (open, base `main`, ready for review; closes nothing).
- Code checkpoint: see `git log`. The token-only `fix(skill)` commit, then one `fix(skill)` commit per finding (17 and 18 share one), then a `docs(skill)` commit.
- Verification: 100 skill tests pass, and each commit passes on its own. Each new test failed before its fix. 17 and 18 were also checked in the browser against a synthetic dataset: the old page closed the session from a stale tab and left the fields editable during a save; the new page refuses the stale finish and locks the fields.
- Compatibility: new snapshots have new IDs, since they include two more files. New known and track references leave out turns shorter than 0.3 s, so they differ from references built before.
- Next action: review and merge PR #22.

## Ranked work

1. #18 Use a two-person two-track call as its own speaker reference: recorder, decision 6, and `review.py tracks` merged in #19. Left: the user listens to session `check-two-track-call` (command in `docs/experiments/2026-10-30-two-track-call.md`), then freeze `ref-check-two-track-call`, run `eval-check-two-track-call` on both runs, write the private report, and finish the summary (Sortformer's 528/629 turns is provisional until then)
2. #4 Add a shareable synthetic test recording (the call merged in #17; the remaining runners still need to run on it)
3. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
4. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (blocks choosing the pipeline's ASR model)
5. #9 Choose a license
6. #7 Decide where private experiment data is backed up
7. #5 Add a Reproduce section to public experiment summaries
8. #3 Migrate the 2026-10-24 experiment results into the private review dataset
9. Remaining code review findings R-08–R-10 and R-13 in `experiments/` runners (no issue yet): model pinning, the no-VAD variant, runner completion checks, sweep output reuse. The second review's finding 20 (the two-track experiment summary's empty commit, malformed snapshot ID, and `git show :path` recovery command) goes with #18. The skill findings merged in #20 and the recorder fixes in #21; the skill follow-ups are in #22
10. Build the minimal pipeline for saved recordings in `experiments/pipelines/`: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet)

## Pending

None.
