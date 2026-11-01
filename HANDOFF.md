# Handoff

## In progress

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

### feat/saved-audio-pipeline

- Task: #28, the first saved-audio to Markdown pipeline. Plan approved 2026-11-01, using Qwen3.5 9B through MLX for the recap and never Ollama: if MLX breaks, stop and ask. PR [#29](https://github.com/pomodorozhong/meeting-recap/pull/29) is ready and open, and says `Related to #28`. Its body was last updated with the user's approval to cover the Who option, and still matches the branch. The branch is unlinked.
- Code checkpoint: `07a547a` plus this handoff commit, pushed. On 2026-11-01 the branch was rebuilt with force-with-lease to hold only the pipeline, the Who option, and README diagrams. The summary accuracy and baseline work moved to stacked branches.
- State:
  - `experiments/pipelines/whisper-sortformer/` runs convert → MLX Whisper → Sortformer (or `--diarizer who`) → attach → `speakers.json` → transcript → recap.
  - The README has a sequence diagram of which process reads and writes which file.
  - Synthetic call: 283 s with Sortformer and 132 s with Who, 6.71 GB MLX peak, transcript speaker agreement 95.1% and 95.8%.
- Verification: 24 pipeline tests, 116 skill tests and 10 experiment tests pass. A second run at `07a547a` reproduced the outputs (see `feat/pipeline-baseline`).
- Next action: wait for review of #29. P-01 is the follow-up the user hasn't approved yet.
- P-01 — Awaiting the user's go-ahead for reproducibility fixes on this branch, raised 2026-11-01 and not answered:
  1. `setup` and `run` check the SHA-256 of the Sortformer weights (FluidAudio downloads them from the repo's `main`, not a revision) and of the Who weights (tag `v0.3.4`, currently commit `f026f46`), and refuse on a mismatch.
  2. Record the Swift, ffmpeg, Python and MLX versions, the Mac model and the memory in `run.json`. Add `.python-version`.
  3. Remove the repeated pins: the README's pin table points at `pins.py`, `Package.resolved` and `uv.lock`, and `pins.py` reads the Swift revisions from `Package.resolved`.
  4. A README "Reproduce" note listing the environment used, and saying other hardware gives close, not identical, results.
  Doing these changes #29 after its body was approved, so its body needs a matching update and approval.

## Ranked work

1. #28 First saved-audio to Markdown pipeline. The scorers next to the synthetic call merged in #30. A PR stack, in merge order: #29 (the pipeline), then `feat/pipeline-baseline` and `feat/recap-accuracy`, rebuilt on both. Then the private-recording trial and review, with a public plan committed first
2. #18 Use a two-person two-track call as its own speaker reference: recorder, decision 6, and `review.py tracks` merged in #19. Left: the user listens to session `check-two-track-call` (command in `docs/experiments/2026-10-30-two-track-call.md`), then freeze `ref-check-two-track-call`, run `eval-check-two-track-call` on both runs, write the private report, and finish the summary (Sortformer's 528/629 turns is provisional until then)
3. #4 Add a shareable synthetic test recording (the call merged in #17; the remaining runners still need to run on it)
4. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
5. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (informs the pipeline's ASR model; #28 starts from Whisper without waiting for it)
6. #9 Choose a license
7. #7 Decide where private experiment data is backed up
8. #5 Add a Reproduce section to public experiment summaries
9. #3 Migrate the 2026-10-24 experiment results into the private review dataset
10. Remaining runner follow-ups (no issue yet): external WhisperKit/FluidAudio model-cache verification, the no-VAD variant, and completion checks outside the HushScribe export fix. Earlier skill, recorder and review fixes merged in #20–#24 and #26.

## Pending

None.
