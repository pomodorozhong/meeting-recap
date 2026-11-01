# Handoff

## In progress

### feat/synthetic-call-scoring

- Task: move scoring against the synthetic call into `experiments/synthetic-call/` so every pipeline and experiment can use it, as the user asked; to merge before #29's stacked PRs. Related to #28 and #4; it closes nothing. Branched from `main`, unlinked.
- Code checkpoint: the scoring commit plus this handoff commit, pushed. No PR yet.
- State:
  - `score_speakers.py` is self-contained and takes the shared runner formats (word-timestamped ASR JSON, `segments`, attached turns) plus the audio or its SHA-256.
  - `score_recap.py` and `reference/recap-key.json` moved from `feat/recap-accuracy` (`experiments/recap-accuracy/score.py` and `key.json`); the key is byte-identical (SHA-256 `4ef8c91b…`).
  - `opencc-python-reimplemented==0.1.7` was added to the folder's uv project; the lock only adds it.
- Verification:
  - 6 new tests in `tests/synthetic_call/` pass.
  - The moved speaker scorer gives the published 98.2%/95.1% (Sortformer) and 98.5%/95.8% (Who) on `feat/pipeline-baseline`'s saved runs.
  - The moved recap scorer gives identical results on all 12 scored recaps of `feat/recap-accuracy`.
  - `generate.py` with seed 7 still produces the committed `call_sha256`, `segments.json` and `transcript.json` byte for byte.
- Next action:
  1. Resolve P-01.
  2. After it merges, rebuild `feat/pipeline-baseline` and `feat/recap-accuracy` to use these scorers, citing PR numbers rather than commit hashes, and keep every experiment's commands reproducible.
- P-01 — Awaiting approval of this branch's PR title and body before opening it against `main`.

### feat/saved-audio-pipeline

- PR #29, open. This copy is not that branch's handoff; read `feat/saved-audio-pipeline`'s own `HANDOFF.md`.

## Ranked work

1. #28 First saved-audio to Markdown pipeline: built on `feat/saved-audio-pipeline` (see its section above); the private-recording trial and review remain
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
