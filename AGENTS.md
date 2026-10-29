# Agent instructions

Local meeting assistant for an M2 Pro / 16 GB Mac. Status: [docs/README.md](docs/README.md). Decisions: [docs/decisions.md](docs/decisions.md). Layout: [README.md](README.md#layout).

<!-- handoff:start (from the handoff skill; edit the skill's template, not this copy) -->
## Handoff

`HANDOFF.md` at the repository root is how sessions resume. It has three sections: `In progress` (one `### <branch>` subsection per active branch, holding its state and its own approval requests), `Ranked work`, and `Pending` (approval requests not tied to a branch). A pending entry, such as `P-01`, records a request, not approval.

- **Start of a session:** read `HANDOFF.md` and the subsection for `git branch --show-current`; none means this branch has no work in progress. Compare its code checkpoint with `git log`, re-check verification made stale by later commits, and run the documented checks before building on it. If this branch's PR merged or closed, follow the `commit` skill's branch-safety rules before committing or pushing. Before recommending or starting work, show each unresolved request that existing authorization doesn't cover, from every branch subsection and `Pending` (marking any a merged or closed PR made obsolete), and each blocking decision in `Ranked work`, and ask the user about them. Pick new work from the default branch's `Ranked work`.
- **Edit only this branch's subsection,** plus `Ranked work` and `Pending` when they actually change. Keep it current rather than a log, and never write secrets.
- **Commit `HANDOFF.md`** only before a push and at wrap-up, as a `docs:` commit on the work branch. Never commit it on the default branch.
- **PRs:** use the `open-pr` skill, and keep its unanswered approval requests in this branch's subsection until they are resolved. **End of a session:** use the `handoff` skill.
- **Before creating a branch, editing `HANDOFF.md`, or resolving a conflict in it,** read the `handoff` skill's working rules (`references/working-rules.md` in that skill).
<!-- handoff:end -->

## This repository is public

- Never commit recordings, transcripts or excerpts of them, participant names, listening answers, meeting-specific prompts, or paths to private files. This covers commit messages, branches, issues, and PRs too.
- Write people as Speaker A/B/C and recordings by duration and kind of call.
- Tests and examples use synthetic or redistributable audio, never a real call.
- Before committing, search the diff for participant names and transcript phrases.

Private material lives in the review dataset outside the checkout, at `$MEETING_REVIEW_DATA` (set up as in [README.md](README.md#setup)). Run experiments on real recordings with the `meeting-experiment-review` skill. Commit each experiment's summary in `docs/experiments/` (from `TEMPLATE.md`) before its first run.

## Conventions

- Each experiment is self-contained in its own `experiments/<name>/` folder; candidate pipelines go in `experiments/pipelines/<name>/`. Nothing imports across experiment folders, and `app/` depends on nothing in `experiments/`.
- Record each decision as a numbered entry in `docs/decisions.md`.
- Conventional Commits.
- Pin models and dependencies by revision or hash.
- Python tools run with `uv` or the standard library. A folder whose Python needs packages is its own uv project: a `pyproject.toml` (`package = false`) and a committed `uv.lock` beside its scripts, run with `uv run --project <folder>` from the repository root or `uv run` inside it. Rerun `uv lock` there after changing its dependencies. Never add a `pyproject.toml` at the repository root; `app/` will be its own project too.
- After changing the skill, run its tests from the repository root (they use generated audio only):

  ```bash
  uv run --no-project --with opencc-python-reimplemented python -m unittest discover -s tests/skill -t tests/skill
  ```
