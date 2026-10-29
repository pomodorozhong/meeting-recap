# Handoff

## In progress

### feat/two-track-capture

- Task: record calls as two aligned tracks and use a two-person call's tracks as its speaker reference; [#18](https://github.com/pomodorozhong/meeting-recap/issues/18). Based on `main`; GitHub cannot link an existing branch, so the PR body must say `Closes #18`.
- PR: none
- Code checkpoint: see `git log`. `feat:` adds `experiments/capture/` (`record.swift`, ScreenCaptureKit, `mic.m4a` + `system.m4a` + `timing.json`); `docs:` adds decision 6; `feat(skill)` adds `scripts/tracks.py` and `review.py tracks` (reference from two tracks' activity, source kind `two_tracks`), documented in SKILL.md.
- State: the user recorded a ~48.5 min two-person call with headphones (in the dataset's `raw/`, with a meeting app's transcript whose speaker labels are wrong: it shows three speakers). A dry run of `tracks.py` on it in scratch took 2 s and found ~15 min of A, ~11 min of B, 91 s overlapping; at the default 30 s window that is 86 clips of ~31 s. Nothing is registered in the dataset yet.
- Verification: 81 skill tests pass (the three new ones fail without the fixes); `swiftc -typecheck experiments/capture/record.swift` passes; the documented `amix` command makes a 16 kHz mono mix of the full call length. Diffs scanned for names and private paths.
- Experiment: [docs/experiments/2026-10-30-two-track-call.md](docs/experiments/2026-10-30-two-track-call.md) is committed (status planned), with run, session, reference and evaluation IDs; skill snapshot `cc24865f…` taken at ``, after two review fixes: artifacts are digest-checked on every read (R-05) and references take answers and revision from one event read (R-06).
- Next action: follow its plan: make the scratch WAVs and AAC mix, register `two-track-call`, register the track-activity run, run Sortformer (timed, nothing else running), build the track reference, then prepare the 10-clip check session for the user.

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
