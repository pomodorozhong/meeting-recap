# Handoff

## In progress

### codex/synthetic-recording-collection

- [Draft PR #32](https://github.com/pomodorozhong/meeting-recap/pull/32) targets `main` and relates to #4. Source checkpoint `d8a859f` appends a three-female localization call to the verified ten-recording corpus. The user asked to expand with other female voices. The collection now has eight scripts and three controls, producing eleven main WAVs.
- Localization uses EmotiVoice 1093, 1012 and 1066. F5 supplies the female roles in the earlier calls, with Qwen male presets. Both dependency environments, model/code artifacts and NLTK resources are pinned. The three EmotiVoice reference auditions reproduce byte for byte, and their level-adjusted Whisper gates pass at 100%, 97.9% and 100%. The F5 handoff gate has its verified 97.9% result. Listening choices are retained outside the public checkout.
- The ten published hash records and seven earlier scripts are verified against `44d0285`. A separate checkout regenerated localization with identical WAV, transcript, speaker intervals and all 15 turn clips. All 33 fixture payloads pass verification, all 32 tests pass, and both dependency locks are current.
- Offline verification and reuse preserve all 207 fixture files and modification times with an empty model cache and invoke no child synthesis process. Both modes refuse altered EmotiVoice speaker provenance without changing outputs.
- A full localization sanity decode reaches 97.6% Mandarin agreement. Onboarding still records the observed whole-call Whisper hallucination around its 12-second pause. Full pipeline benchmarks remain a follow-up.
- F5 pretrained weights carry CC-BY-NC-4.0 terms and its demo reference archive states no separate redistribution terms. EmotiVoice and encoder upstream license references and provenance are documented. The added CPU runtime preserves the audition's Torch 2.10.0 and Transformers 4.57.6 versions.
- The update and PR-body replacement are authorized. The body uses What changed / Why / Verification / Related issue / reference. Next action is review of the eleven-fixture PR #32.

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

### feat/saved-audio-pipeline

- Task: #28, the first saved-audio to Markdown pipeline. Plan approved 2026-11-01, using Qwen3.5 9B through MLX for the recap and never Ollama: if MLX breaks, stop and ask. PR [#29](https://github.com/pomodorozhong/meeting-recap/pull/29) is ready and open, and says `Related to #28`. The branch is unlinked.
- Code checkpoint: `67c85f7`, on top of a merge of `main` (with #30). The approved reproducibility fixes (old P-01) are committed but not pushed, so #29 still shows `3aa501a`.
- State:
  - `experiments/pipelines/whisper-sortformer/` runs convert → MLX Whisper → Sortformer (or `--diarizer who`) → attach → `speakers.json` → transcript → recap.
  - `setup` and `run` refuse diarizer weights whose folder SHA-256 differs from `pins.py` (Sortformer `a5cb7e5…`, Who `b19f474…`). `run.json` records those digests and the environment. `.python-version` is 3.12. `pins.py` reads the Swift revisions from `Package.resolved`.
  - The README has a Reproduce note that scores the call with `experiments/synthetic-call/score_speakers.py`.
- Verification at `67c85f7`:
  - 29 pipeline tests, 116 skill tests, 10 experiment tests and 7 synthetic-call tests pass.
  - `setup --who` printed both pinned digests.
  - `run --no-summary` on the call, scored with the README's command, gave Sortformer 98.2%/95.1% and Who 98.5%/95.8%.
  - `render`, `summarize` and the recap stage were not rerun after the change.
- Next action: resolve P-02, then wait for review of #29.
- P-02 — Awaiting approval to push `67c85f7` and replace #29's body with the updated draft shown in the session. That draft adds the weight digests, the environment record, the single-place pins, the Reproduce note, 29 tests, and step 6 of How to verify. Pushing is authorized, but changing the approved body is not.

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
