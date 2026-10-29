# Handoff

## In progress

### build/uv-projects

- Task: make every Python tool folder a uv project with a committed lock (no issue); based on `main`, independent of `feat/synthetic-call`.
- PR: https://github.com/pomodorozhong/meeting-recap/pull/15 (open, base `main`; awaiting review). Replaces the closed #13.
- Code checkpoint: see `git log`. `pyproject.toml` (`package = false`) and `uv.lock` in `experiments/breeze/`, `experiments/mlx/`, `experiments/pyannote/`, `experiments/transcription/` and the skill folder; the scripts lost their inline headers. `AGENTS.md`, `docs/runners.md` and `SKILL.md` describe running with `uv run --project <folder>`.
- Verification: each project installs with `uv run --locked`, and each script gets past its imports. The MLX Whisper runner ran on a 5.5-minute synthetic call, and `metrics.py` read its output. `pick_clips.py --help` runs in the skill project. 67 skill tests pass; `uv lock --check` passes in all five projects.
- Checks not run: the Breeze and pyannote runners past startup (pyannote needs the user's Hugging Face token).
- Next action: the user reviews #15. If the synthetic call PR merges first, add `experiments/synthetic-call/` to the AGENTS.md line as the example project.

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
