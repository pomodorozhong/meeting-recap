# Handoff

## In progress

### docs/repository-layout

- Task: decide the repository layout (closes #8); also carries the handoff layout commit from the merged foundation branch.
- PR: none yet; branch is linked to #8 and pushed without these commits
- Code checkpoint: d232880
- State: complete for review. `docs/decisions.md` holds all decisions, including the layout: self-contained `experiments/<name>/`, candidate pipelines in `experiments/pipelines/<name>/`, and `app/` for the final app with its own copy of the chosen pipeline. README.md and AGENTS.md updated.
- Verification: docs only; diff scanned for names and private paths.
- Next action: open the PR with the `open-pr` skill once the user approves it.
- Avoid: branching from local `main`, which is still at the initial commit; base new branches on `origin/main`.

### feat/synthetic-call

- Task: shareable synthetic test recording (advances #4); stacked on `docs/repository-layout`.
- PR: none
- State: `experiments/synthetic-call/` holds `script.json`, `generate.py` (CosyVoice 2, voices bootstrapped from CosyVoice-300M-SFT), and a README; not committed. The user listens to `out/call.wav` before deciding on the voices, the script, and whether to commit audio.
- Next action: apply the user's listening feedback, then commit and add a skill reference built from `segments.json`.

## Ranked work

1. #4 Add a shareable synthetic test recording (in progress on `feat/synthetic-call`)
2. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
3. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (blocks choosing the pipeline's ASR model)
4. #9 Choose a license
5. #7 Decide where private experiment data is backed up
6. #5 Add a Reproduce section to public experiment summaries
7. #3 Migrate the 2026-10-24 experiment results into the private review dataset
8. Build the minimal pipeline for saved recordings in `experiments/pipelines/`: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet)

## Pending

None.
