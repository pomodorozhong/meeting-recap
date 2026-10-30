# Handoff

## In progress

### fix/capture-runner-alignment

- Task: fix two findings from the second review of `5332001`. The recorder now pads a track that goes quiet before the stop to the other track's end (finding 2). `run_full.sh` now refuses inputs that share a basename, or outputs already in `OUT`, before any model starts (finding 10). No issue. Built from `main` at `d0f6d19`, unlinked.
- PR: https://github.com/pomodorozhong/meeting-recap/pull/24 (open, base `main`, ready for review; closes nothing; independent of #23).
- Code checkpoint: see `git log`; one `fix(capture)` and one `fix(experiments)` commit.
- Verification: `swiftc -typecheck` passes. A probe built from the recorder's own `Track`/`stop()` code with generated buffers gave files of 2.048 s and 0.512 s before the fix, and 2.048 s for both after. `run_full.sh` was run with fake model tools: same-name inputs and a rerun into the same `OUT` both exit 2, and unique inputs keep both outputs. Not run: a live recording.
- Next action: review and merge PR #24 (in any order with #23).

### fix/skill-scoring-checks

- Task: fix the skill findings from the second review of `5332001` that #20–#22 left open. Native playback now stays inside the clip (1). `--mappings` must name every run scored (3). Split same-label spans now score like continuous ones (4). `__unassigned__` can never be mapped (5). Validation lists run folders without `run.json` under `incomplete_runs` (6). Run times past the recording are refused (7). A fractional `skip_before` is no longer rounded down (8). A reused snapshot is checked file by file (9). No issue. Built from `main` at `d0f6d19`, unlinked.
- PR: https://github.com/pomodorozhong/meeting-recap/pull/23 (open, base `main`, ready for review; closes nothing; independent of #24).
- Code checkpoint: see `git log`; five `fix(skill)` commits, then this `docs:` commit.
- Verification: 109 skill tests pass on the branch and on each commit. Each new test failed before its fix. The page test needs Node and is skipped without it. Not run: the review page in a real browser.
- Compatibility: `validate` output has a new `incomplete_runs` key. Runs with times more than 1 s past the recording's `duration_seconds` now fail `add-run` and `validate`.
- Next action: review and merge PR #23 (in any order with #24).

## Ranked work

1. #18 Use a two-person two-track call as its own speaker reference: recorder, decision 6, and `review.py tracks` merged in #19. Left: the user listens to session `check-two-track-call` (command in `docs/experiments/2026-10-30-two-track-call.md`), then freeze `ref-check-two-track-call`, run `eval-check-two-track-call` on both runs, write the private report, and finish the summary (Sortformer's 528/629 turns is provisional until then)
2. #4 Add a shareable synthetic test recording (the call merged in #17; the remaining runners still need to run on it)
3. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
4. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (blocks choosing the pipeline's ASR model)
5. #9 Choose a license
6. #7 Decide where private experiment data is backed up
7. #5 Add a Reproduce section to public experiment summaries
8. #3 Migrate the 2026-10-24 experiment results into the private review dataset
9. Remaining code review findings R-08–R-10 and R-13 in `experiments/` runners (no issue yet): model pinning, the no-VAD variant, runner completion checks, sweep output reuse. The second review's finding 20 (the two-track experiment summary's empty commit, malformed snapshot ID, and `git show :path` recovery command) goes with #18. The skill findings merged in #20 and the recorder fixes in #21; the skill follow-ups merged in #22; the remaining findings from the second review of `5332001` are in #23 (skill) and #24 (recorder and `run_full.sh`)
10. Build the minimal pipeline for saved recordings in `experiments/pipelines/`: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet)

## Pending

None.
