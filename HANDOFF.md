# Handoff

## In progress

### build/lock-uv-scripts

- Task: make every Python tool folder a uv project with a committed lock (no issue); stacked on `docs/repository-layout`, which now holds the merged #12.
- PR: none yet; awaiting the user's approval to open it.
- Code checkpoint: see `git log`. `pyproject.toml` (`package = false`) and `uv.lock` in `experiments/breeze/`, `experiments/mlx/`, `experiments/pyannote/`, `experiments/transcription/` and the skill folder; the scripts lost their inline headers. `AGENTS.md`, `docs/runners.md` and `SKILL.md` describe running with `uv run --project <folder>`.
- Verification: each project installs with `uv run --locked`, and each script gets past its imports. The MLX Whisper runner ran on the synthetic call, and `metrics.py` read its output (same results as before). `pick_clips.py --help` runs in the skill project. 70 skill tests pass.
- Checks not run: the Breeze and pyannote runners past startup (pyannote needs the user's Hugging Face token).
- Next action: open the PR once the user approves it, based on `docs/repository-layout`.

### docs/repository-layout

- Task: decide the repository layout (closes #8); also carries the handoff layout commit from the merged foundation branch.
- PR: none yet; branch is linked to #8 and pushed
- Code checkpoint: d232880
- State: complete for review. `docs/decisions.md` holds all decisions, including the layout: self-contained `experiments/<name>/`, candidate pipelines in `experiments/pipelines/<name>/`, and `app/` for the final app with its own copy of the chosen pipeline. README.md and AGENTS.md updated.
- Verification: docs only; diff scanned for names and private paths.
- Next action: open the PR with the `open-pr` skill once the user approves it.
- Avoid: branching from local `main`, which is still at the initial commit; base new branches on `origin/main`.

## Ranked work

1. #4 Add a shareable synthetic test recording (the call, its reference and `review.py known` merged into `docs/repository-layout` with #12; still open because its done-when says "each runner", and only Sortformer and the MLX Whisper runner have run on the call)
2. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
3. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (blocks choosing the pipeline's ASR model)
4. #9 Choose a license
5. #7 Decide where private experiment data is backed up
6. #5 Add a Reproduce section to public experiment summaries
7. #3 Migrate the 2026-10-24 experiment results into the private review dataset
8. Build the minimal pipeline for saved recordings in `experiments/pipelines/`: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet)

## Pending

None.
