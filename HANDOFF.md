# Handoff

## In progress

### feat/two-track-capture

- Task: record calls as two aligned tracks and use a two-person call's tracks as its speaker reference; [#18](https://github.com/pomodorozhong/meeting-recap/issues/18). Based on `main`, unlinked. The PR does not finish #18 (its experiment has not run), so it says `Related to #18`.
- PR: https://github.com/pomodorozhong/meeting-recap/pull/19 (open, base `main`, ready for review; `Related to #18`, closes nothing).
- Code checkpoint: see `git log`. `feat:` adds `experiments/capture/` (`record.swift`, ScreenCaptureKit, `mic.m4a` + `system.m4a` + `timing.json`); `docs:` adds decision 6; `feat(skill)` adds `scripts/tracks.py` and `review.py tracks` (reference from two tracks' activity, source kind `two_tracks`), documented in SKILL.md.
- State: the user recorded a ~48.5 min two-person call with headphones (in the dataset's `raw/`, with a meeting app's transcript whose speaker labels are wrong: it shows three speakers). A dry run of `tracks.py` on it in scratch took 2 s and found ~15 min of A, ~11 min of B, 91 s overlapping; at the default 30 s window that is 86 clips of ~31 s. Nothing is registered in the dataset yet.
- Verification: 81 skill tests pass (the three new ones fail without the fixes); `swiftc -typecheck experiments/capture/record.swift` passes; the documented `amix` command makes a 16 kHz mono mix of the full call length. Diffs scanned for names and private paths.
- Experiment: [docs/experiments/2026-10-30-two-track-call.md](docs/experiments/2026-10-30-two-track-call.md) is committed (status planned), with run, session, reference and evaluation IDs; skill snapshot `cc24865f…` taken at ``, after two review fixes: artifacts are digest-checked on every read (R-05) and references take answers and revision from one event read (R-06).
- Experiment state: recording `two-track-call`, runs `tracks-two-track-call` and `sortformer-two-track-call`, reference `tracks-two-track-call` (86 clips), evaluation `eval-two-track-call` (Sortformer 528/629 turns, 39/86 clips, provisional), and session `check-two-track-call` (10 clips) are in the dataset; scratch WAVs are in a session scratchpad and can be remade from the plan.
- Next action: the user listens to `check-two-track-call` (command in the experiment summary); then freeze `ref-check-two-track-call`, run `eval-check-two-track-call` on both runs, write the private report, and finish the summary.

## Ranked work

1. #18 Use a two-person two-track call as its own speaker reference (in progress on `feat/two-track-capture`)
2. #4 Add a shareable synthetic test recording (the call merged in #17; the remaining runners still need to run on it)
3. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
4. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (blocks choosing the pipeline's ASR model)
5. #9 Choose a license
6. #7 Decide where private experiment data is backed up
7. #5 Add a Reproduce section to public experiment summaries
8. #3 Migrate the 2026-10-24 experiment results into the private review dataset
9. Remaining code review findings (R-01–R-04, R-07–R-14; no issue yet): dataset validation of references and evaluations, attachment gaps and empty or zero-length words, snapshot concurrency, model pinning, runner wrappers, transcript clip picking, writes outside the dataset guard
10. Build the minimal pipeline for saved recordings in `experiments/pipelines/`: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet)

## Pending

None.
