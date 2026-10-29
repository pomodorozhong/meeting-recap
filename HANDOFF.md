# Handoff

## In progress

### feat/synthetic-call

- Task: shareable synthetic test recording (advances #4, unlinked); based on `main`, independent of `build/uv-projects`.
- PR: not yet opened. The same work was reviewed as #12, which merged into the layout branch by mistake before that branch had a PR to `main`; it was split back out so #14 stayed focused on the layout.
- Code checkpoint: see `git log`. `feat(skill)` adds `review.py known` with tests; `feat:` adds `experiments/synthetic-call/` as a uv project: `generate.py` (Qwen3-TTS CustomVoice; A `vivian`, B `dylan`, C `ryan`, `aiden` spare), the 73-turn `script.json` (5.5 min), and `reference/` from the seed-7 run.
- State: awaiting review. Audio is not committed: seed 7 reproduces the same `call_sha256` on this machine, also in the locked project environment. Whisper heard the call at 5.9% character error rate. 70 skill tests pass. Sortformer, scored with `review.py known`, recovered 67/72 turns and 7/10 clips.
- Next action: the user reviews the PR. #4 stays open: its done-when says "each runner", but only Sortformer and the MLX Whisper runner have run on the call.
- Avoid: Kokoro and CosyVoice voices; cloning; using `review.py known` for a real call.

## Ranked work

1. #4 Add a shareable synthetic test recording (awaiting review on `feat/synthetic-call`; then the remaining runners on the call)
2. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
3. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (blocks choosing the pipeline's ASR model)
4. #9 Choose a license
5. #7 Decide where private experiment data is backed up
6. #5 Add a Reproduce section to public experiment summaries
7. #3 Migrate the 2026-10-24 experiment results into the private review dataset
8. Build the minimal pipeline for saved recordings in `experiments/pipelines/`: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet)

## Pending

None.
