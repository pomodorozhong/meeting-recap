# Handoff

## In progress

### codex/synthetic-collection

- Related to #4, #11 and #28. Local branch without a PR. Source checkpoint `cac52ea`, measured results and replayable verdicts `742cc5d`.
- Seventeen materialized synthetic recordings. The seven-recording ASR and diarization matrix is documented in the [collection report](docs/experiments/2026-11-01-synthetic-collection.md). The ten independent action calls and frozen keys are in `experiments/synthetic-call/action-scripts/`. Their [action benchmark](docs/experiments/2026-11-01-action-evidence.md) compares exact and recovered inputs, ordinary and focused extraction, label repair, citation verification and two pinned ASRs.
- All source checks at `cac52ea` passed in a clean checkout: 18 synthetic, 30 pipeline, 116 skill and 10 experiment tests. Rebuild either suite with the synthetic-call generator. All 70 case/condition scores replayed byte for byte from the local outputs. Full Whisper + focused recovered 7/14 strict actions, Turbo + focused 4/14. The staged citation verifier rejected every candidate.
- Next independent synthetic check: evaluate recovery of the task object, recipient and deadline from imperfect transcripts on new scripts, including no-action controls. Real-call listening remains a separate task.

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

## Ranked work

1. #28 First saved-audio to Markdown pipeline. The scorers next to the synthetic call merged in #30. The pipeline merged in #29. Pending stack work is `feat/pipeline-baseline` and `feat/recap-accuracy`, rebuilt on both. Then the private-recording trial and review, with a public plan committed first
2. #18 Use a two-person two-track call as its own speaker reference: recorder, decision 6, and `review.py tracks` merged in #19. Left: the user listens to session `check-two-track-call` (command in `docs/experiments/2026-10-30-two-track-call.md`), then freeze `ref-check-two-track-call`, run `eval-check-two-track-call` on both runs, write the private report, and finish the summary (Sortformer's 528/629 turns is provisional until then)
3. #4 Add a shareable synthetic test recording (the call merged in #17; 17 recordings, including the ten-call evidence-backed action benchmark, on `codex/synthetic-collection`, with no PR yet)
4. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization (next, as the user asked; its issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`)
5. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy on confirmed real speech, following the synthetic CER comparison
6. #9 Choose a license
7. #7 Decide where private experiment data is backed up
8. #5 Add a Reproduce section to public experiment summaries
9. #3 Migrate the 2026-10-24 experiment results into the private review dataset
10. Remaining runner follow-ups (no issue yet): external WhisperKit/FluidAudio model-cache verification, the no-VAD variant, and completion checks outside the HushScribe export fix. Earlier skill, recorder and review fixes merged in #20–#24 and #26.

## Pending

None.
