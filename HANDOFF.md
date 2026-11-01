# Handoff

## In progress

### feat/pipeline-baseline

- Task: make the synthetic-call baseline in #29's README reproducible with saved run outputs. Related to #28; it closes nothing. Was stacked on `feat/saved-audio-pipeline`, which merged as #29 (after #30); the branch has not been rebuilt on `main` yet. Unlinked.
- Code checkpoint: `7a850b7` plus the handoff commits, pushed. No PR yet.
- State:
  - `experiments/pipelines/whisper-sortformer/baseline/2026-11-01/` holds a second run of each diarizer at `07a547a`, without audio or local paths, with its environment recorded.
  - It reproduced the first runs' Whisper output, Sortformer segments and recaps exactly. The Sortformer recap here is the one the recap accuracy summary says "was not kept", so that line can be corrected.
  - The branch also has its own `score_speakers.py`. The user decided it belongs in `experiments/synthetic-call/`, which #30 merged.
  - `main` now has #29's reproducibility fixes: weight digests checked by `setup` and `run`, the environment in `run.json`, and a README Reproduce note that already scores the call with `experiments/synthetic-call/score_speakers.py`. A fresh rerun at #29 gave the published figures (Sortformer 98.2%/95.1%, Who 98.5%/95.8%).
- Verification: 26 pipeline tests pass, and both saved runs score as documented.
- Next action: rebuild this branch on `main` now (#29 and #30 have both merged), then run the pipeline tests.
  - Drop the pipeline's `score_speakers.py` and its test, and score with the synthetic-call scorer.
  - Cite PR #29 instead of the `07a547a` hash.
  - Point the saved runs' README at #29's Reproduce note instead of repeating it. Say the saved `run.json` files predate the environment and weight-digest fields.
  - Revise P-01's body (base `main`, no stacking note), and ask again.
- P-01 — Awaiting approval to open a ready PR from `feat/pipeline-baseline` against `main` (originally `feat/saved-audio-pipeline`, now merged), titled `feat(pipelines): save the synthetic baseline runs and score their speakers`, with the exact body below. The open-pr skill needs approval of the finished branch and body; pushing is already authorized, opening a PR is not. The user changed the plan before answering, so this draft must be revised after the rebuild (it describes the pipeline's own scorer and cites a commit hash). It is kept as the starting point.

#### P-01 proposed PR body

```markdown
Stacked on #29. Review and merge #29 first; this PR's base then changes to `main`.

## What changed

- Add `experiments/pipelines/whisper-sortformer/score_speakers.py`. It recomputes the speaker agreement figures in the pipeline README's synthetic baseline from a run folder:
  - **Diarization agreement:** each Whisper word is labelled at its own time by the run and by the known turns.
  - **Transcript agreement:** transcript characters are aligned to the script's text, so text Whisper put in the wrong turn counts.
  - Both use the best label mapping.
  - It refuses a run whose input isn't the call the reference describes.
- Add `baseline/2026-11-01/`, the saved outputs of the pipeline on the synthetic call with each diarizer: `asr.json`, raw and converted diarization, `turns.json`, `speakers.json`, `transcript.md`, `summary.*`, `run.json`, `stages.json` and the `/usr/bin/time -l` reports.
  - Both runs are at commit `07a547a`, with the environment recorded in its README.
  - Audio and logs with local paths are left out. One path field in `sortformer.raw.json` was rewritten, and the README says so.
- Add `tests/pipelines/test_score_speakers.py`, which checks a split voice, boundary drift and a mismatched input, on generated files.
- Link the pipeline README's baseline section to the saved runs and the script.

## Why

The baseline numbers in #29's README came from two scratch scripts and runs that only existed on one machine, so nobody could check or recompute them. This PR keeps that measurement separate from the pipeline code.

The saved runs are a second run, made to check repeatability:
- Whisper's output, Sortformer's segments and the recaps came out identical to the first runs.
- The agreement figures are the same: Sortformer 98.2% and 95.1%, Who 98.5% and 95.8%.
- Stage times came within 6%. The exception is Who's 2-second diarize step, where the difference is process start-up.

## Verification

### Automated checks

- `uv run --project experiments/pipelines/whisper-sortformer python -m unittest discover -s tests/pipelines -t tests/pipelines`: 26 tests pass.
- `uv run --project experiments/pipelines/whisper-sortformer experiments/pipelines/whisper-sortformer/score_speakers.py experiments/pipelines/whisper-sortformer/baseline/2026-11-01/<sortformer|who>`: gives the figures above.
- `git diff --check` and a scan of the saved files for local paths and names: pass.
- Not run: the pipeline on another Mac. The README says to expect close, not identical, results there.

### How to verify

1. Run the `score_speakers.py` command on both saved runs. Expected: 98.2% and 95.1% for Sortformer, 98.5% and 95.8% for Who.
2. Optional, with the pipeline set up and the synthetic call generated: rerun `recap.py run` on `call.wav` into a new folder and score it. Expected: the same figures on an M2 Pro with macOS 26.6.2. Elsewhere, expect close figures.

Verified: steps 1 and 2 on an M2 Pro with 16 GB (the saved runs are step 2's output). Reviewer follow-up: none required.

## Related issues

Related to #28: makes the pipeline's synthetic baseline reproducible. The issue stays open for the private-recording review.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants. It was stacked on #29, which has merged; rebuild it on `main` with the synthetic-call scorer and key from #30. Read that branch's own `HANDOFF.md`.

## Ranked work

1. #28 First saved-audio to Markdown pipeline. The pipeline (#29) and the scorers next to the synthetic call (#30) merged. Next, rebuild `feat/pipeline-baseline` and `feat/recap-accuracy` on `main` and open their PRs. Then the private-recording trial and review, with a public plan committed first
2. #18 Use a two-person two-track call as its own speaker reference: recorder, decision 6, and `review.py tracks` merged in #19. Left: the user listens to session `check-two-track-call` (command in `docs/experiments/2026-10-30-two-track-call.md`), then freeze `ref-check-two-track-call`, run `eval-check-two-track-call` on both runs, write the private report, and finish the summary (Sortformer's 528/629 turns is provisional until then)
3. #4 Add a shareable synthetic test recording (the call merged in #17 and its scorers in #30; the remaining runners still need to run on it)
4. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
5. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (informs the pipeline's ASR model; #28 starts from Whisper without waiting for it)
6. #9 Choose a license
7. #7 Decide where private experiment data is backed up
8. #5 Add a Reproduce section to public experiment summaries
9. #3 Migrate the 2026-10-24 experiment results into the private review dataset
10. Remaining runner follow-ups (no issue yet): external WhisperKit/FluidAudio model-cache verification, the no-VAD variant, and completion checks outside the HushScribe export fix. Earlier skill, recorder and review fixes merged in #20–#24 and #26.

## Pending

None.
