# Handoff

## In progress

### codex/synthetic-collection

- Related to #4, #11 and #28. Local, unlinked branch without a PR. Source checkpoint `d4021b4`; original inference source `cac52ea`, measured results and semantic verdicts `742cc5d`. The prepared branch remains unpushed.
- Seventeen synthetic recordings: the [collection report](docs/experiments/2026-11-01-synthetic-collection.md) covers seven, and the [action benchmark](docs/experiments/2026-11-01-action-evidence.md) covers ten calls, 14 commitments and 70 case/condition results. Full Whisper + focused recovered 7/14 strict actions, Turbo + focused 4/14; the verifier rejected every candidate. A public synthetic-only bundle now preserves 200 original scoring files; audio and remaining raw outputs stay outside tracked files.
- The [methodology audit](docs/experiments/2026-11-01-action-evidence-review.md) and [falsification plan](docs/experiments/2026-11-01-action-grounding-plan.md) remain applicable: intended-script agreement plus citations does not establish faithful recovery of useful commitments. The 60 extraction probes and 36 verifier controls are prepared; calibration and batch execution follow on `codex/action-grounding-sequence`. No model inference has run on those probes in this branch.
- All four reproducibility findings are fixed: original score inputs are replayable without models, setup caches both ASRs and preflights the full action matrix, shell helpers use locked project interpreters, and the three FluidAudio model folders have immutable recovery sources with verified file hashes. The original result report and semantic verdicts are unchanged.
- Verification at `d4021b4`, 2026-11-02: all 192 tests passed in a separate detached checkout (24 synthetic, 37 pipeline, 116 skill, 10 experiment, five grounding). Model-free replay matched every published cell, aggregate and recorded timing. All three uv locks, shell syntax and diff checks passed. An initial new integration-test fixture omitted an HTML asset; the corrected fixture passes. Tests requiring macOS `/usr/bin/time` ran outside its restrictive execution sandbox.
- Recovery/setup checks: all 61 model files downloaded into an empty temporary cache and matched the three original folder hashes. A fresh Swift build completed at the pinned revisions. Real setup with both cached ASRs/Qwen and a three-second Sortformer silence warmup passed. An isolated cache missing full Whisper failed before creating results; complete-cache preflight passed. Earlier repeat checks matched one synthetic call's published audio hash twice, all 229 grounding files, and derived-control artifacts. Full inference matrices and independent semantic regrading were not rerun.
- Next action: obtain P-02 publication approval for this finished branch and body, then push and open one draft PR against `main`. This is the first independent PR and the prerequisite of `codex/action-grounding-sequence`, which should be rebuilt after merge. The baseline and recap-accuracy branches can each be rebuilt independently on `main`.
- Existing remote handoff notes: [#4](https://github.com/pomodorozhong/meeting-recap/issues/4#issuecomment-6559734124) and [#28](https://github.com/pomodorozhong/meeting-recap/issues/28#issuecomment-6559734484). They predate these reproducibility fixes; no new remote comments were posted.
- P-02 — Publication remains unapproved. Branch/base: `codex/synthetic-collection` → `main`; status: draft; title: `feat(experiments): add synthetic benchmarks for ASR and action recovery`. The exact revised body is below. The open-pr skill requires approval of the finished branch and body before publication. Local review files under ignored `.agents/propose-stack/synthetic-collection/` record the final tip, tree and commit list. No push or PR creation is authorized. This branch is unlinked and closes no issues.

#### P-02 proposed PR body

````markdown
The original synthetic call could not show how transcription and speaker attribution affect action recovery across different meetings. Add seven ASR/speaker benchmark inputs and ten fictional action calls with 14 frozen commitments, along with repeatable runners and saved measurements.

- Add pinned Turbo Q4 as an opt-in ASR; full Whisper remains the default.
- Add focused-action extraction, citation verification, seven-condition scoring, a methodology audit, and 60 extraction probes plus 36 verifier controls.
- Include 200 original synthetic scoring artifacts so a fresh checkout can replay all 70 published results without models.
- Cache both ASRs with `setup --asr all`, preflight the complete action matrix, use locked Python environments in shell helpers, and restore Sortformer, LS-EEND and Community-1 from immutable revisions with file and folder hashes.

The historical synthetic comparison recovered 7/14 strictly supported actions with full Whisper plus focused extraction, versus 4/14 with Turbo. The verifier rejected all nine candidates. These results remain exploratory; the audit documents limits in reference validity, grading and transfer.

## Verification

All 192 tests passed, including in a separate detached checkout of the committed fix:

- `uv run --locked --project experiments/synthetic-call python -m unittest discover -s tests/synthetic_call -t tests/synthetic_call` — 24 passed.
- `uv run --locked --project experiments/pipelines/whisper-sortformer python -m unittest discover -s tests/pipelines -t tests/pipelines` — 37 passed.
- `uv run --no-project --with opencc-python-reimplemented python -m unittest discover -s tests/skill -t tests/skill` — 116 passed.
- `uv run --no-project python -m unittest discover -s tests/experiments -t tests/experiments` — 10 passed.
- `uv run --no-project python -m unittest discover -s experiments/action-grounding/tests -v` — 5 passed.

The tests cover changed replay inputs, missing models/shards, interrupted downloads, preservation of changed caches, and real review-skill subprocesses with an unusable system Python. An initial integration-test fixture omitted the skill's HTML asset; the corrected fixture passes. Model inference is stubbed in the unit suites.

Verified model-free replay:

```bash
uv run --no-project --python 3.12 python experiments/synthetic-call/replay_actions.py check
```

Expected and observed: all 70 results, aggregate fields and recorded timings match the original report.

Also verified:

- Downloaded all 61 diarizer files into an empty temporary cache with `weights.py setup sortformer ls-eend speaker-diarization --root RESTORED`; all three original folder hashes matched.
- Built `fluidaudiocli` from pinned Swift dependencies. `recap.py setup --asr all` completed using cached pinned ASRs/Qwen and a real three-second silence warmup; `preflight --asr all` passed.
- An isolated cache missing full Whisper stopped the action runner before it created results. Adding the snapshot made preflight pass.
- Two regenerations of the existing 21.78-second synthetic negative control matched its published audio hash. Two grounding preparations matched all 229 files; derived-control transformations also repeated exactly.
- All three `uv lock --check` commands, shell syntax checks and `git diff --check` passed.

Not rerun: the complete seven-recording or 70-condition inference matrices, or independent semantic regrading. Replay checks saved measurements; it does not establish identical model output on other hardware. The READMEs provide full benchmark commands for reviewer follow-up.

## Dependencies and issues

Targets `main` with no unmerged prerequisites. The follow-on `codex/action-grounding-sequence` branch depends on this change and should be rebuilt after merge.

Related to #4 (synthetic inputs), #11 (ASR comparisons), and #28 (downstream action recovery). Confirmed real-speech evaluation and private-recording review remain open. Closes no issues.
````

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

## Ranked work

1. Publish the independent synthetic-collection foundation related to #4, #11 and #28 after P-02 approval. Then rebuild `codex/action-grounding-sequence` on the merged foundation: its evaluator, runner and stopped-calibration report depend on this branch's prompts and fixtures. Prioritize benchmark validity before another model sweep.
2. #28 First saved-audio to Markdown pipeline. The scorers next to the synthetic call merged in #30. The pipeline merged in #29. Pending stack work is `feat/pipeline-baseline` and `feat/recap-accuracy`, rebuilt on both. Then the private-recording trial and review, with a public plan committed first
3. #18 Use a two-person two-track call as its own speaker reference: recorder, decision 6, and `review.py tracks` merged in #19. Left: the user listens to session `check-two-track-call` (command in `docs/experiments/2026-10-30-two-track-call.md`), then freeze `ref-check-two-track-call`, run `eval-check-two-track-call` on both runs, write the private report, and finish the summary (Sortformer's 528/629 turns is provisional until then)
4. #4 Add a shareable synthetic test recording (the call merged in #17; 17 recordings, including the ten-call evidence-backed action benchmark, on `codex/synthetic-collection`, with no PR yet)
5. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
6. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy on confirmed real speech, following the synthetic CER comparison
7. #9 Choose a license
8. #7 Decide where private experiment data is backed up
9. #5 Add a Reproduce section to public experiment summaries
10. #3 Migrate the 2026-10-24 experiment results into the private review dataset
11. Remaining runner follow-ups (no issue yet): external WhisperKit/FluidAudio model-cache verification, the no-VAD variant, and completion checks outside the HushScribe export fix. Earlier skill, recorder and review fixes merged in #20–#24 and #26.

## Pending

None.
