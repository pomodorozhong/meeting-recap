# Agent instructions

Local meeting assistant for an M2 Pro / 16 GB Mac. Status: [docs/README.md](docs/README.md). Decisions: [docs/decisions.md](docs/decisions.md). Layout: [README.md](README.md#layout).

## This repository is public

- Never commit recordings, transcripts or excerpts of them, participant names, listening answers, meeting-specific prompts, or paths to private files. This covers commit messages, branches, issues, and PRs too.
- Write people as Speaker A/B/C and recordings by duration and kind of call.
- Tests and examples use synthetic or redistributable audio, never a real call.
- Before committing, search the diff for participant names and transcript phrases.

Private material lives in the review dataset outside the checkout, at `$MEETING_REVIEW_DATA` (set up as in [README.md](README.md#setup)). Run experiments on real recordings with the `meeting-experiment-review` skill. Commit each experiment's summary in `docs/experiments/` (from `TEMPLATE.md`) before its first run.

## Conventions

- Each experiment is self-contained in its own `experiments/<name>/` folder; candidate pipelines go in `experiments/pipelines/<name>/`. Nothing imports across experiment folders, and `app/` depends on nothing in `experiments/`.
- Each experiment has one entry-point script that runs everything up to any step only a person can do, and its summary follows `docs/experiments/TEMPLATE.md` (decision 11).
- Record each decision as a numbered entry in `docs/decisions.md`.
- Conventional Commits.
- Pin models and dependencies by revision or hash.
- Python tools run with `uv` or the standard library. A folder whose Python needs packages is its own uv project: a `pyproject.toml` (`package = false`) and a committed `uv.lock` beside its scripts, run with `uv run --project <folder>` from the repository root or `uv run` inside it. Rerun `uv lock` there after changing its dependencies. Never add a `pyproject.toml` at the repository root; `app/` will be its own project too.
- After changing the skill, run its tests from the repository root (they use generated audio only):

  ```bash
  uv run --no-project --with opencc-python-reimplemented python -m unittest discover -s tests/skill -t tests/skill
  ```
- After changing `app/`, run `app/scripts/bundle.sh --test` from anywhere. It runs the tests (generated audio only) and rebuilds the app bundle. The package has no dependencies, so it needs no lock file.
