# Handoff

## In progress

### codex/fix-review-findings

- Task: finish the approved review fixes against `main` at `b5a03ae`; plan approved 2026-10-31. Related to #18 and #5; neither is fully resolved. The branch is unlinked, closes no issues, and has no PR yet.
- Code checkpoint: `e46e31e` plus this handoff commit; eight local commits cover exact timestamp bounds, explicit noise calibration, prediction padding, HushScribe export errors, model revision enforcement, sweep output reservation, historical recovery docs, and overlap regression coverage.
- State: implementation is complete and committed locally. Existing private references, evaluations, recordings, and public scores were not changed. No model weights were downloaded. Prior review fixes already merged in #20–#24 were preserved.
- Verification: 116 skill tests and 10 experiment tests pass. All eight commits were verified independently in a temporary detached worktree. MLX and pyannote locks check, sweep syntax checks, the HushScribe patch applies to its pinned public source, and historical recovery reproduces the original nine-file snapshot digest. Not run: live capture, private experiments, real model inference, or a full HushScribe GUI build.
- Compatibility: uncertain automatic track gates now require an explicit measured noise floor; that value is recorded per speaker. New track times preserve sample precision. Sweep `OUT` must not already exist. Unlisted MLX models and revision overrides require a full commit SHA. Pyannote writes a metadata sidecar. Historical experiments use their frozen code, not the current skill.
- Next action: resolve P-01, then push without force, open the approved ready PR, verify its contents and closing references, and attach it to the chat.
- P-01 — Awaiting final publish approval: push `codex/fix-review-findings` and open a ready PR against `main`, titled `fix: close remaining experiment review and reproducibility gaps`, with the exact body below. The open-pr skill requires approval of the finished branch and body before any push. Plan approval does not cover publishing.

#### P-01 proposed PR body

```markdown
## What changed

- Preserve sample-derived track times and selected clip bounds so rounding cannot put generated artifacts past the recording's end.
- Refuse an automatic noise gate that would erase all activity above the absolute floor. Both track commands accept an explicit per-speaker noise calibration, and references record it. This guard does not replace the listening check.
- Include saved padding in displayed speaker and transcript predictions, matching the evaluated range.
- Propagate HushScribe diarization-export and result-write failures into failed trial status and nonzero exits. Regenerate the patch against its pinned upstream revision.
- Load immutable MLX and pyannote model revisions. MLX loads a verified local snapshot; pyannote passes the revision to the bundled pipeline and writes registration metadata. Reject moving revision names and document offline-cache requirements.
- Reserve a fresh sweep output directory before any model starts and convert only the five declared raw CLI outputs. Retain earlier and partial runs.
- Repair the two-track experiment's recovery instructions using a public commit verified to reproduce its original snapshot digest. Keep the actual run-time checkout commit explicitly unknown, and correct the runtime comparison.
- Add regression coverage for these cases and the overlapping-word interval fix already present on main. No private data or experiment scores are changed.

## Why

The remaining review findings could erase an active speaker from a reference, reject valid generated timestamps, show predictions for a different range than scoring, report success without saved artifacts, load moving model revisions, or overwrite sweep results. The experiment recovery record also lacked a usable historical checkpoint.

## Verification

### Automated checks

- `uv run --no-project --with opencc-python-reimplemented python -m unittest discover -s tests/skill -t tests/skill`: 116 tests pass.
- `uv run --no-project python -m unittest discover -s tests/experiments`: 10 tests pass, using generated fixtures, mocked model calls, and the patch's actual Swift export/finalization functions.
- `uv lock --check --project experiments/mlx` and `uv lock --check --project experiments/pyannote`: pass.
- `zsh -n experiments/diarization/run_sweep.sh`: passes.
- Each fix/test/documentation commit was checked independently in a temporary detached worktree with the suites available at that commit.
- The HushScribe patch passes forward application checking against all three files at upstream commit `51103f0c8f97344ec7ecdf6480a2ee53cd9a0e92`.
- The documented archive/replay procedure reproduces snapshot `cc24865fadea9fba01b8fe4ca722a978bbeb8b1faaa56ae671e0ccf4635b354a` from public commit `53320016ef6eaf07e95936ebbef51546d95ef59b`.
- `git diff --check` and a scan of added lines for private paths/content: pass.
- Not run: live capture, private-dataset experiments, real model inference, or a full HushScribe GUI build. These checks use generated data and avoid downloading model weights.

### How to verify

1. Run the two unittest commands above. Expected: all 126 tests pass on macOS with Swift, Node, and zsh available.
2. The regressions verify fractional recording ends, calibration refusal/recovery and provenance, saved prediction padding, export failures, exact model revision loading, and sweep rerun preservation.
3. Follow the recovery commands in `docs/experiments/2026-10-30-two-track-call.md` to extract the historical skill without changing the current checkout.

Verified: all steps above on macOS using generated fixtures. Reviewer follow-up: real-model inference and full GUI validation remain available for the next scheduled experiment; neither was performed here.

## Related issues

Related to #18: improves track-reference correctness and recovery; its listening check remains pending.
Related to #5: repairs this experiment's recovery instructions; the other summaries remain outside this change.

No issues are closed, and the branch is not linked to an issue.
```

## Ranked work

1. #18 Use a two-person two-track call as its own speaker reference: recorder, decision 6, and `review.py tracks` merged in #19. Left: the user listens to session `check-two-track-call` (command in `docs/experiments/2026-10-30-two-track-call.md`), then freeze `ref-check-two-track-call`, run `eval-check-two-track-call` on both runs, write the private report, and finish the summary (Sortformer's 528/629 turns is provisional until then)
2. #4 Add a shareable synthetic test recording (the call merged in #17; the remaining runners still need to run on it)
3. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
4. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (blocks choosing the pipeline's ASR model)
5. #9 Choose a license
6. #7 Decide where private experiment data is backed up
7. #5 Add a Reproduce section to public experiment summaries
8. #3 Migrate the 2026-10-24 experiment results into the private review dataset
9. Remaining runner follow-ups (no issue yet): external WhisperKit/FluidAudio model-cache verification, the no-VAD variant, and completion checks outside the HushScribe export fix. Earlier skill and recorder fixes merged in #20–#24; the approved remaining review fixes are implemented locally on `codex/fix-review-findings`, awaiting P-01.
10. Build the minimal pipeline for saved recordings in `experiments/pipelines/`: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet)

## Pending

None.
