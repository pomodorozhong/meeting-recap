# Handoff

## In progress

### docs/repository-layout

- Task: decide the repository layout (closes #8); also carries the handoff layout commit from the merged foundation branch.
- PR: none yet; branch is linked to #8 and pushed
- Code checkpoint: d232880
- State: complete for review. `docs/decisions.md` holds all decisions, including the layout: self-contained `experiments/<name>/`, candidate pipelines in `experiments/pipelines/<name>/`, and `app/` for the final app with its own copy of the chosen pipeline. README.md and AGENTS.md updated.
- Verification: docs only; diff scanned for names and private paths.
- Next action: open the PR with the `open-pr` skill once the user approves it.
- Avoid: branching from local `main`, which is still at the initial commit; base new branches on `origin/main`.

### feat/synthetic-call

- Task: shareable synthetic test recording (advances #4); stacked on `docs/repository-layout`.
- PR: none
- Code checkpoint: see `git log`; the experiment commit holds `generate.py` (Qwen3-TTS CustomVoice only), the 73-turn `script.json` (5.5 min; A `vivian`, B `dylan`, C `ryan`, `aiden` spare), and `reference/` from the seed-7 run.
- State: the user approved the four Qwen3 voices and the full-length script; they have not said whether the full call sounds right. Audio is not committed: seed 7 reproduces the same `call_sha256` on this machine. The skill gained `review.py known`, which builds a reference from known segments (tests added; 70 skill tests pass). End to end on the call: Sortformer recovered 67/72 turns and got 7/10 clips fully right.
- Next action: the user listens to the call; then open a PR for #4 (stacked on `docs/repository-layout`, or after it merges). #4's done-when says "each runner", but only Sortformer has run so far; the ASR runners have nothing to score against except `reference/transcript.json` by hand.
- Avoid: Kokoro and CosyVoice voices; cloning; using `review.py known` for a real call.

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
