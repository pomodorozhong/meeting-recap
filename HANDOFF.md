# Handoff

## In progress

### feat/two-track-capture

- Task: record calls as two aligned tracks and use a two-person call's tracks as its speaker reference; [#18](https://github.com/pomodorozhong/meeting-recap/issues/18). Based on `main`; GitHub cannot link an existing branch, so the PR body must say `Closes #18`.
- PR: none
- Code checkpoint: 2d915a4. `feat:` adds `experiments/capture/` (`record.swift`, ScreenCaptureKit, `mic.m4a` + `system.m4a` + `timing.json`); `docs:` adds decision 6.
- State: the user recorded a ~48.5 min two-person call with headphones (in the dataset's `raw/`, with a meeting app's transcript whose speaker labels are wrong: it shows three speakers). Nothing has run on it yet.
- Verification: `swiftc -typecheck experiments/capture/record.swift` passes; the user's recording shows both tracks written and aligned within 0.2 s. Diffs scanned for names and private paths.
- Next action: add a skill command that builds a reference from two tracks' voice activity (with tests on generated audio), then write the experiment summary in `docs/experiments/` and register the mixed recording.

## Ranked work

1. #18 Use a two-person two-track call as its own speaker reference (in progress on `feat/two-track-capture`)
2. #4 Add a shareable synthetic test recording (the call merged in #17; the remaining runners still need to run on it)
3. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
4. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (blocks choosing the pipeline's ASR model)
5. #9 Choose a license
6. #7 Decide where private experiment data is backed up
7. #5 Add a Reproduce section to public experiment summaries
8. #3 Migrate the 2026-10-24 experiment results into the private review dataset
9. Build the minimal pipeline for saved recordings in `experiments/pipelines/`: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet)

## Pending

None.
