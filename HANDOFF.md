# Handoff

## In progress

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

### feat/saved-audio-pipeline

- PR #29, the pipeline, open for review. Read that branch's own `HANDOFF.md`.

### feat/synthetic-call-scoring

- Task: put scoring against the synthetic call next to its reference, so every pipeline and experiment can use it. The user asked for this PR to merge first. Related to #28 and #4; it closes nothing. Branched from `main`, unlinked.
- Code checkpoint: `d9691b9` plus the handoff commits, pushed. No PR yet.
- State:
  - `score_speakers.py` is self-contained. It takes the shared runner formats (word-timestamped ASR JSON, `segments`, attached turns) plus the audio or its SHA-256.
  - `score_recap.py` and `reference/recap-key.json` moved unchanged from `feat/recap-accuracy` (`experiments/recap-accuracy/score.py` and `key.json`). The key is byte-identical (SHA-256 `4ef8c91b…`). The verdict counts now print in a fixed order.
  - `opencc-python-reimplemented==0.1.7` was added to the folder's uv project; the lock only adds it.
- Verification:
  - 6 new tests in `tests/synthetic_call/`, 116 skill tests and 10 experiment tests pass.
  - The speaker scorer gives the published 98.2%/95.1% (Sortformer) and 98.5%/95.8% (Who) on `feat/pipeline-baseline`'s saved runs.
  - The recap scorer gives identical results on all 12 scored recaps of `feat/recap-accuracy`.
  - `generate.py` with seed 7 still produces the committed `call_sha256`, `segments.json` and `transcript.json` byte for byte.
- Next action:
  1. Resolve P-01.
  2. Once it merges, rebuild `feat/pipeline-baseline` and `feat/recap-accuracy` to use these scorers instead of their own copies, citing PR numbers rather than commit hashes. Recheck that every documented command still reproduces its numbers.
- P-01 — Awaiting approval to open a ready PR from `feat/synthetic-call-scoring` against `main`, titled `feat(synthetic-call): score speaker labels and recaps against the call`, with the exact body below. The open-pr skill needs approval of the finished branch and body; pushing is already authorized, opening a PR is not.

#### P-01 proposed PR body

```markdown
## What changed

- Add `experiments/synthetic-call/score_speakers.py`, which scores a run's speaker labels against the call's known turns, over characters, with the best label mapping:
  - **Diarization agreement:** each Whisper word is labelled at its own time by the run and by the known turns.
  - **Transcript agreement:** the run's attached turns are aligned to the script's text after OpenCC `t2s`, so a word placed in the wrong turn counts as an error.
  - **Inputs:** the formats every runner writes (word-timestamped ASR JSON, `segments`, attached turns) and the run's audio or its SHA-256. It refuses audio that isn't this call, and ASR text without word timestamps.
- Add `experiments/synthetic-call/score_recap.py` and `reference/recap-key.json`. The key lists 24 items a correct recap of the call holds (10 decisions, 11 action items with owners and deadlines, 2 proposals, 1 open question) and 7 questions the call answers. The scorer reports, from hand verdicts:
  - key items found and placed correctly;
  - evidence coverage;
  - recap items by verdict;
  - owners and deadlines.
- Add `opencc-python-reimplemented==0.1.7` to the folder's uv project. The lock adds only that package.
- Add `tests/synthetic_call/test_scoring.py`, with generated run files. It covers a split voice, a word in the wrong turn, the audio and word-timestamp refusals, and recap scoring with renamed speakers.
- Document both scorers in the synthetic-call README, including where the key came from and its SHA-256.

## Why

The synthetic call is the project's shared ground truth, but scoring against it lived inside individual branches. The pipeline had a speaker scorer, and the recap accuracy work had a key and a recap scorer. Putting both next to the reference, and merging them first, lets every pipeline and experiment measure itself the same way without importing another experiment's code. The pipeline-baseline and recap-accuracy PRs will be rebuilt on top of this.

## Verification

### Automated checks

- `uv run --project experiments/synthetic-call python -m unittest discover -s tests/synthetic_call -t tests/synthetic_call`: 6 tests pass.
- `uv run --no-project --with opencc-python-reimplemented python -m unittest discover -s tests/skill -t tests/skill`: 116 tests pass.
- `uv run --no-project python -m unittest discover -s tests/experiments`: 10 tests pass.
- `uv lock --check --project experiments/synthetic-call`: passes.
- `git diff --check` and a scan for local paths and names: pass.

### Reproducibility checks

- **The call still reproduces.** `generate.py` with seed 7, run with the updated lock, produced the committed `call_sha256` (`6b7011c6…`) and byte-identical `reference/segments.json` and `reference/transcript.json`.
- **The speaker scorer reproduces published figures.** On the saved pipeline runs from the upcoming baseline PR it gives Sortformer 98.2% and 95.1%, and Who 98.5% and 95.8%, the figures #29's README reports.
- **The recap scorer reproduces published figures.** On all 12 recaps scored in the recap accuracy work it gives the same results as the scorer there. The key is byte-identical to the one used (SHA-256 `4ef8c91b…`). One change: verdict counts now come out in a fixed order instead of set order.

### How to verify

1. Run the three test commands above. Expected: all pass.
2. Optional, with the call generated: `uv run --project experiments/synthetic-call experiments/synthetic-call/score_speakers.py --asr <asr.json> --segments <segments.json> --audio experiments/synthetic-call/out/script/call.wav` on any runner's output. Expected: agreement figures, or a refusal if the audio isn't this call.

Verified: step 1, and both reproducibility checks above, on an M2 Pro with 16 GB and macOS 26.6.2. Reviewer follow-up: step 2.

## Related issues

Related to #4: adds scoring to the shareable synthetic recording. The other runners still need to run on it.
Related to #28: the pipeline's baseline and recap accuracy are measured with these scorers.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Ranked work

1. #28 First saved-audio to Markdown pipeline. A PR stack, in merge order: `feat/synthetic-call-scoring` (scorers next to the synthetic call; merge first) and #29 (the pipeline; independent of it), then `feat/pipeline-baseline` and `feat/recap-accuracy`, rebuilt on both. Then the private-recording trial and review, with a public plan committed first
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
