# Handoff

## In progress

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline, stacked on #29; to be rebuilt on the synthetic-call scorer. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Task: measure and improve the pipeline's recap accuracy, as the user asked after #29 opened. Related to #28; it closes nothing. Stacked on `feat/saved-audio-pipeline` (#29). Unlinked.
- Code checkpoint: `9742c14` plus the handoff commits, pushed. No PR yet.
- State:
  - `docs/experiments/2026-11-01-recap-accuracy-synthetic.md` has both plans, committed before their runs, and the results. `experiments/recap-accuracy/` holds the key, scorer, harnesses, verdicts and every scored recap.
  - v0: a recap of the perfect script found 21/24 items but listed answered questions as open; the pipeline recaps found 13 and 20.
  - v1 cut wrong items 24→7 but failed the committed rule (67 vs 69 found, swing 7 vs 6). v2 changed nothing.
  - The default stays v0, and the variants stay in `pipeline.py`.
- Verification: 24 pipeline tests pass, and `score.py` reproduces every table.
- Next action:
  1. Once `feat/synthetic-call-scoring` merges, rebuild this branch:
     - drop `key.json` and `score.py` and use `experiments/synthetic-call/score_recap.py` and `reference/recap-key.json`;
     - update the summary's commands and say the key moved unchanged (same SHA-256);
     - correct the line saying the first Sortformer recap wasn't kept, since `feat/pipeline-baseline` reproduced it;
     - cite PR numbers instead of hashes;
     - revise P-01's body.
  2. The user chooses the next recap round: a v3 that fixes v1's open-question and deadline losses (planned and committed first, same rule), sampling several recaps and keeping the items they agree on, or a different local model.
- P-01 — Awaiting approval to open a ready PR from `feat/recap-accuracy` against `feat/saved-audio-pipeline`, titled `docs(experiments): measure recap accuracy and test summary-stage variants`, with the exact body below. The open-pr skill needs approval of the finished branch and body; pushing is already authorized, opening a PR is not. Not answered before the user re-planned the stack. Revise it after the rebuild (paths of the key and scorer change).

#### P-01 proposed PR body

```markdown
Stacked on #29. Review and merge #29 first; this PR's base then changes to `main`.

## What changed

- Add `experiments/recap-accuracy/`, which measures how accurate the pipeline's recap is on the synthetic call:
  - `key.json`: 24 items a correct recap must hold (10 decisions, 11 action items with owners and deadlines, 2 proposals, 1 open question), written from the script before any recap was scored, plus 7 questions the call answers.
  - `score.py`: scores one recap against the key from hand verdicts in `matches/`. It reports items found and correctly placed, evidence coverage, verdict counts, owners and deadlines.
  - `script_recap.py` and `recap_variant.py`: recap the script itself, the script with speaker names rotated, or a pipeline transcript, through the pipeline's summary stage, run as a command.
  - `runs/` and `matches/`: every scored recap and its transcript, with the verdict and a note per item.
- Add summary-stage variants to `pipeline.py` and `summary_stage.py`: v1 (stricter rules) and v2 (v1 plus a check pass against the whole transcript), chosen by an optional third argument. The pipeline's default and its behaviour are unchanged (v0).
- Add `docs/experiments/2026-11-01-recap-accuracy-synthetic.md`, with both plans committed before their runs, the results and the decisions. Re-rank the pipeline README's issues so the recap comes first.

## Why

The recap is what a user reads, but nothing measured it. A recap of the perfect script found 21 of 24 items, yet listed 4 answered questions as open. The pipeline recaps found 13 (Sortformer) and 20 (Who), with 5–7 wrong items each, and a recap swings with small changes to its input. So the summary stage needs fixing before ASR or diarization are tuned for it.

Results of the variant round, over four inputs:
- **v1:** cut wrong items from 24 to 7 and misplaced ones from 9 to 0. It also stopped listing open questions, wrote effort estimates as deadlines, and found 67 items against v0's 69.
- **v2:** returned v1's draft essentially unchanged at twice the time.
- **Outcome:** neither met the decision rule committed before the runs, so the default stays v0.

## Verification

### Automated checks

- `uv run --project experiments/pipelines/whisper-sortformer python -m unittest discover -s tests/pipelines -t tests/pipelines`: 24 tests pass. The variant code adds no tests; v0 output is unchanged.
- `python3 experiments/recap-accuracy/score.py experiments/recap-accuracy/runs/<run> experiments/recap-accuracy/matches/<run>.json`: run on the scored runs. The numbers agree with the experiment summary.
- `git diff --check` and a scan for private paths: pass.
- The branch's tree is identical to the work as first pushed, apart from `HANDOFF.md`.
- Not run: any private recording.

### How to verify

1. Score any run with the `score.py` command above. Expected: the figures in the summary's tables.
2. Read a few files in `matches/` against `key.json` and the run's `summary.json` to check the hand verdicts. Claude wrote the key and judged each item, knowing the variant.
3. Optional, with the pipeline's models set up: `python3 experiments/recap-accuracy/recap_variant.py script <new folder> v1`. Expected: the same recap as `runs/v1-script`, since decoding is greedy.

Verified: step 1 on an M2 Pro with 16 GB. Repeatability was checked with v0 on the script, which gave byte-identical replies in two runs; step 3 itself was not rerun. Reviewer follow-up: steps 2 and 3.

## Related issues

Related to #28: measures the recap's support and omissions, which the issue's review criteria ask for. The private-recording review is still to do, so the issue stays open.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### feat/saved-audio-pipeline

- PR #29, the pipeline, open for review. Read that branch's own `HANDOFF.md`.

### feat/synthetic-call-scoring

- Scorers next to the synthetic call, from `main`, to merge first; PR awaiting approval. Read that branch's own `HANDOFF.md`.

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
