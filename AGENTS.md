# Agent instructions

Local meeting assistant for an M2 Pro / 16 GB Mac. Status and next steps: [HANDOFF.md](HANDOFF.md). Layout: [README.md](README.md).

## This repository is public

- Never commit recordings, transcripts or excerpts of them, participant names, listening answers, meeting-specific prompts, or paths to private files. This covers commit messages, branches, issues, and PRs too.
- Write people as Speaker A/B/C and recordings by duration and kind of call.
- Tests and examples use synthetic or redistributable audio, never a real call.
- Before committing, search the diff for participant names and transcript phrases.

Private material lives in the review dataset outside the checkout, at `$MEETING_REVIEW_DATA`. Run experiments on real recordings with the `meeting-experiment-review` skill. Commit each experiment's summary in `docs/experiments/` (from `TEMPLATE.md`) before its first run.

## Conventions

- Conventional Commits.
- Pin models and dependencies by revision or hash.
- Python tools run with `uv` or the standard library.
