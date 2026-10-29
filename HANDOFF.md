# Handoff

## In progress

### feat/two-track-capture

- Task: record calls as two aligned tracks and use a two-person call's tracks as its speaker reference; no issue yet (see P-01). Based on `main`, unlinked.
- PR: none
- Code checkpoint: 2d915a4. `feat:` adds `experiments/capture/` (`record.swift`, ScreenCaptureKit, `mic.m4a` + `system.m4a` + `timing.json`); `docs:` adds decision 6.
- State: the user recorded a ~48.5 min two-person call with headphones (in the dataset's `raw/`, with a meeting app's transcript whose speaker labels are wrong: it shows three speakers). Nothing has run on it yet.
- Verification: `swiftc -typecheck experiments/capture/record.swift` passes; the user's recording shows both tracks written and aligned within 0.2 s. Diffs scanned for names and private paths.
- Next action: add a skill command that builds a reference from two tracks' voice activity (with tests on generated audio), then write the experiment summary in `docs/experiments/` and register the mixed recording.
- Pending: P-01 (file an issue for this branch) blocks linking the branch and opening its PR.

## Ranked work

1. #4 Add a shareable synthetic test recording (the call merged in #17; the remaining runners still need to run on it)
2. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
3. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (blocks choosing the pipeline's ASR model)
4. #9 Choose a license
5. #7 Decide where private experiment data is backed up
6. #5 Add a Reproduce section to public experiment summaries
7. #3 Migrate the 2026-10-24 experiment results into the private review dataset
8. Build the minimal pipeline for saved recordings in `experiments/pipelines/`: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet)

## Pending

- P-01: file an issue "Use a two-person two-track call as its own speaker reference" (recorder, decision 6, a skill command building the reference from track voice activity, and a first experiment scoring Sortformer on it). Needs approval because it posts to GitHub; blocks linking `feat/two-track-capture` and its PR.
