# Handoff

## In progress

### codex/synthetic-collection

- Related to #4, #11 and #28. Local, unlinked branch without a PR. Latest source/audit checkpoint `0249985`; inference source `cac52ea`, measured results and replayable verdicts `742cc5d`. These commits are unpushed and unavailable on another computer.
- Seventeen materialized synthetic recordings. The [collection report](docs/experiments/2026-11-01-synthetic-collection.md) covers seven recordings; the [action benchmark](docs/experiments/2026-11-01-action-evidence.md) covers ten independent calls, 14 intended commitments and 70 case/condition results. Full Whisper + focused recovered 7/14 strict actions, Turbo + focused 4/14; the staged verifier rejected every candidate. Generated audio and raw outputs remain local outside tracked files. Regenerate audio with the synthetic-call collection commands if needed.
- The [audit](docs/experiments/2026-11-01-action-evidence-review.md) identifies the shared unproven assumption that intended-script agreement plus citations measures faithful recovery of useful commitments. TTS fidelity, evidence dependence, grader validity and transfer remain unverified; words, timing, boundaries and attribution are confounded. Existing scores remain unchanged.
- The [falsification plan](docs/experiments/2026-11-01-action-grounding-plan.md) and [probe generator](experiments/action-grounding/README.md) define 60 exact-text extraction cases and 36 verifier controls, with a family-level development/holdout split. Fixtures were materialized and validated. No new inference has run. Stage 1 still needs evaluator calibration and batch orchestration; later component, acoustic-transfer and long-context stages are designs, not implemented runners.
- Verification on `f8b6fb9`, 2026-11-02: 18 synthetic, 30 pipeline, 116 skill, 10 experiment and five grounding-fixture tests passed. The first pipeline attempt hit the execution sandbox's restriction on `/usr/bin/time` reading `kern.clockrate`; the unchanged suite passed outside that sandbox. Fixture CLI generation produced 60 extraction cases and 36 verifier controls. Shell syntax, diff whitespace, JSON parsing and all 70 result cells' aggregate counts passed. Model inference and raw-output verdict replay were not rerun during PR preparation; the earlier replay at `cac52ea` remains historical verification.
- Next action: obtain P-02 publication approval for this independent foundation PR against `main`. The user asked to prioritize an existing branch with no unmerged prerequisites. This branch meets that criterion and is the prerequisite of `codex/action-grounding-sequence`; the latter should be rebuilt after this PR merges. The baseline and recap-accuracy branches can each be rebuilt independently on `main`.
- Remote handoff notes posted and verified on [#4](https://github.com/pomodorozhong/meeting-recap/issues/4#issuecomment-6559734124) and [#28](https://github.com/pomodorozhong/meeting-recap/issues/28#issuecomment-6559734484). These notes describe local work; they do not publish its commits.
- P-02 — Awaiting approval to push `codex/synthetic-collection` and open a draft PR against `main`, titled `feat(experiments): add synthetic benchmarks for ASR and action recovery`, with the exact body below. The open-pr skill requires approval of the finished branch and body before publication. The review request is prepared locally under the ignored `.agents/propose-stack/synthetic-collection/` folder. No push or PR creation is authorized. The branch is unlinked, and the PR closes no issues.

#### P-02 proposed PR body

````markdown
## What changed

- Add a reproducible synthetic collection: seven ASR/speaker benchmark inputs and ten action-recovery calls with 14 frozen commitments. The runners preserve per-case outputs, timings, input digests and failures.
- Add pinned `--asr turbo-q4` support to pipeline setup and execution. Record the selected ASR in `run.json` and reject resuming with a different model. Full Whisper remains the default.
- Add experimental focused-action and citation-verification modes, seven-condition action scoring, digest-bound semantic verdicts, and reports for 70 case/condition results.
- Add a methodology audit and a grounding probe generator with 60 extraction cases, 36 verifier controls and a family-level development/holdout split. Calibration and batch execution follow in a separate change.

## Why

The original synthetic call could not show how transcription, speaker attribution and recap quality vary across different scripts and recording conditions. This change makes those comparisons reproducible and measures whether final tasks, owners, deadlines and supporting evidence survive the complete pipeline.

The recorded experiments found lower ASR latency with Turbo Q4, while full Whisper plus focused extraction recovered 7/14 strictly supported actions versus Turbo's 4/14 on the ten new calls. The experimental verifier rejected all nine candidates. These are exploratory synthetic results; the audit records limitations in spoken-reference validity, grading, timestamp identity and transfer to real meetings.

## Verification

### Automated checks

- `uv run --locked --project experiments/synthetic-call python -m unittest discover -s tests/synthetic_call -t tests/synthetic_call`: 18 passed.
- `uv run --locked --project experiments/pipelines/whisper-sortformer python -m unittest discover -s tests/pipelines -t tests/pipelines`: 30 passed.
- `uv run --no-project --with opencc-python-reimplemented python -m unittest discover -s tests/skill -t tests/skill`: 116 passed.
- `uv run --no-project python -m unittest discover -s tests/experiments -t tests/experiments`: 10 passed.
- `uv run --no-project python -m unittest discover -s experiments/action-grounding/tests -v`: 5 passed.
- `bash -n experiments/synthetic-call/benchmark.sh experiments/synthetic-call/compare_fast.sh` and `git diff --check origin/main...HEAD`: passed.
- Parsed all 17 changed JSON files and checked that the 70 action-result cells reproduce the committed aggregate counts.

The first pipeline test attempt failed because the execution sandbox denied `/usr/bin/time` access to `kern.clockrate`; the same suite passed outside that sandbox. Model stages in these tests use generated data and fakes.

Not rerun during PR preparation: audio synthesis, model inference, or semantic-verdict replay against the original local raw outputs. The experiment reports document the earlier runs; the aggregate check above checks their arithmetic.

### How to verify

1. Generate the grounding fixtures without loading models:

   ```bash
   PROBES_PARENT=$(mktemp -d)
   uv run --no-project python experiments/action-grounding/prepare.py "$PROBES_PARENT/pack"
   ```

   Expected: 60 extraction cases, 36 verification cases, and a `prepared-not-run` manifest. Reusing the destination must fail.

2. Follow the pipeline README's Swift-build prerequisites, then use synthetic audio and a fresh output directory outside Git:

   ```bash
   P=experiments/pipelines/whisper-sortformer
   uv run --locked --project "$P" "$P/recap.py" setup --asr turbo-q4 --who
   uv run --locked --project "$P" "$P/recap.py" run "$AUDIO" "$OUT" --asr turbo-q4 --diarizer who
   ```

   Expected: timestamped `transcript.md`, `summary.md`, and the pinned Turbo model in `run.json`. The synthetic-call README documents the full collection and action matrices.

Verified during PR preparation: step 1 and all automated checks. Reviewer follow-up: step 2 and optional full benchmark reproduction.

## Dependencies

Targets `main` with no unmerged prerequisites. The follow-on `codex/action-grounding-sequence` branch uses the prompts and fixtures introduced here and should be rebuilt after this PR merges.

## Related issues

- Related to #4: expands the shareable synthetic inputs and runner coverage.
- Related to #11: adds synthetic ASR comparisons; the confirmed real-speech comparison remains open.
- Related to #28: measures downstream action recovery; the private-recording review remains open.

Closes no issues.
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
