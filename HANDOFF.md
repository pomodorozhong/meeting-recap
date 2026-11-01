# Handoff

## In progress

### codex/synthetic-collection

- Related to #4, #11 and #28. Local, unlinked branch without a PR. Latest source/audit checkpoint `0249985`; inference source `cac52ea`, measured results and replayable verdicts `742cc5d`. These commits are unpushed and unavailable on another computer.
- Seventeen materialized synthetic recordings. The [collection report](docs/experiments/2026-11-01-synthetic-collection.md) covers seven recordings; the [action benchmark](docs/experiments/2026-11-01-action-evidence.md) covers ten independent calls, 14 intended commitments and 70 case/condition results. Full Whisper + focused recovered 7/14 strict actions, Turbo + focused 4/14; the staged verifier rejected every candidate. Generated audio and raw outputs remain local outside tracked files. Regenerate audio with the synthetic-call collection commands if needed.
- The [audit](docs/experiments/2026-11-01-action-evidence-review.md) identifies the shared unproven assumption that intended-script agreement plus citations measures faithful recovery of useful commitments. TTS fidelity, evidence dependence, grader validity and transfer remain unverified; words, timing, boundaries and attribution are confounded. Existing scores remain unchanged.
- The [falsification plan](docs/experiments/2026-11-01-action-grounding-plan.md) and [probe generator](experiments/action-grounding/README.md) define 60 exact-text extraction cases and 36 verifier controls, with a family-level development/holdout split. Fixtures were materialized and validated. No new inference has run. Stage 1 still needs evaluator calibration and batch orchestration; later component, acoustic-transfer and long-context stages are designs, not implemented runners.
- Verification: five grounding-fixture tests passed at `0249985`, along with diff and document-link checks. Earlier source at `cac52ea` passed 18 synthetic, 30 pipeline, 116 skill and 10 experiment tests in a clean checkout; all 70 recorded scores replayed byte for byte. Those suites were not rerun for the isolated new fixture pack or this documentation-only handoff.
- Next action: implement Stage 0 evaluator controls and unique evidence identity, then a serial Stage 1 runner for the two frozen extractors and verifier. Preserve failures, keep expected keys out of inference, freeze repairs before holdout, and follow the two-hour matrix cap. The user requested unattended experiments only; real-call listening is separate.
- Remote handoff notes posted and verified on [#4](https://github.com/pomodorozhong/meeting-recap/issues/4#issuecomment-6559734124) and [#28](https://github.com/pomodorozhong/meeting-recap/issues/28#issuecomment-6559734484). These notes describe local work; they do not publish its commits.
- P-02 — Publishing request pending: push `codex/synthetic-collection` and all its existing local commits to `origin` for remote recovery. No push or PR creation is authorized. This blocks cross-computer retrieval, not continued local experiments. Raw audio and benchmark outputs are not included.

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

## Ranked work

1. Local action-grounding work related to #4 and #28: calibrate the evaluator and run the frozen evidence-intervention/verifier matrix; see the branch subsection. Prioritize benchmark validity before another model sweep.
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
