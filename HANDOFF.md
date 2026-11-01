# Handoff

## In progress

### feat/saved-audio-pipeline

- Task: #28, the first saved-audio to Markdown pipeline. Plan approved 2026-11-01, using Qwen3.5 9B through MLX for the recap and never Ollama: if MLX breaks, stop and ask. The private-recording trial goes in a later PR. The branch is unlinked; PR [#29](https://github.com/pomodorozhong/meeting-recap/pull/29) (ready, open) says `Related to #28`; its body was updated on 2026-11-01 with the user's approval to cover the Who option.
- Code checkpoint: the Who commit plus this handoff commit, pushed. On 2026-11-01 the branch was rebuilt (force-with-lease) to hold only the pipeline and the Who option; the summary accuracy work moved to `feat/recap-accuracy`, stacked on this branch.
- State:
  - `experiments/pipelines/whisper-sortformer/` runs convert → MLX Whisper → Sortformer → attach → speaker mapping → transcript → recap.
  - `--diarizer who`, added at the user's request after #29 opened, swaps in Who (int8).
  - Synthetic call: 283 s with Sortformer and 132 s with Who, for 5:29 of audio, with 6.71 GB MLX peak. Transcript speaker agreement is 95.1% with Sortformer and 95.8% with Who.
  - The ranked issues are in that folder's README; the top one is words crossing turn boundaries.
- Verification:
  - 24 pipeline tests, 116 skill tests and 10 experiment tests pass.
  - Real `setup`, `setup --who`, `run` with each diarizer, `render` with a merge, `summarize` refusal and `summarize --replace` were run on the synthetic call.
- Next action: wait for review of #29. The private-recording trial needs a public experiment plan committed first; summary-stage work continues on `feat/recap-accuracy`.

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
