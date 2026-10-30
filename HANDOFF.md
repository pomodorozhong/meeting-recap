# Handoff

## In progress

### feat/who-diarization

- Task: #1, evaluating Who against Sortformer.
  - Runner `experiments/who/` uses `desert-ant-core` v4.2.1 and weights v0.3.4. It builds with the Command Line Tools.
  - The summary is `docs/experiments/2026-10-30-who-diarization.md`.
  - Built from `main` at `b5a03ae`. The branch is local and not linked to #1, because the PR may not finish the issue until the long calls are scored.
- PR: https://github.com/pomodorozhong/meeting-recap/pull/25 (draft, base `main`, closes nothing; related to #1 and #18).
- Code checkpoint: `798d04a`, then this `docs:` commit.
- State:
  - Weights are in `~/Library/Caches/meeting-recap/who`, outside the checkout.
  - The dataset has the new recording `synthetic`, reference `truth-synthetic`, and runs `who-{fp16,int8}-{synthetic,two-track-call,part1,part2}` and `sortformer-synthetic`.
  - Evaluations `eval-who-synthetic` and `eval-who-two-track-call` are done, and the private report is `reports/eval-who-two-track-call.md`. `dataset.py validate` passes.
- Results:
  - Who scores 64/72 on the synthetic call and 516/629 on the two-track call. Sortformer scores 67/72 and 527/629.
  - Who runs 45–185 times faster than Sortformer, with about half its memory. int8 scores the same as fp16.
  - Repeat runs are byte-identical, and the offline check passed.
  - Provisional decision: Sortformer stays the diarizer, and Who is an optional alternative.
- Waiting on the user:
  - Answer session `full-calls-2026-10-29`, then freeze `ref-full-calls-2026-10-29` and run `eval-who-part1` and `eval-who-part2`.
  - Answer `check-two-track-call` (also #18). If the track reference changes, rerun the two-track evaluation under a new ID.
  - The serve commands are in the summary.
- Not run: no listening yet. Who's minor labels (7–14 s on the long calls) have not been heard.
- Next action: after the user's listening, score the long calls, finalize the decision in the summary and in `docs/decisions.md`, then mark PR #25 ready for review.

## Ranked work

1. #18 Use a two-person two-track call as its own speaker reference: recorder, decision 6, and `review.py tracks` merged in #19. Left: the user listens to session `check-two-track-call` (command in `docs/experiments/2026-10-30-two-track-call.md`), then freeze `ref-check-two-track-call`, run `eval-check-two-track-call` on both runs, write the private report, and finish the summary (Sortformer's 528/629 turns is provisional until then; it is 527/629 under the current skill snapshot, see the Who summary)
2. #1 Evaluate Who: runs and provisional scores done on `feat/who-diarization`; the long calls wait for the user to answer `full-calls-2026-10-29` (issue still cites `experiments/diarization/score.py`, now the skill's `evaluate.py`, and an excerpt that is not in the dataset)
3. #4 Add a shareable synthetic test recording (the call merged in #17; Sortformer and Who have now run on it, the ASR runners still need to)
4. #11 Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy (blocks choosing the pipeline's ASR model)
5. #9 Choose a license
6. #7 Decide where private experiment data is backed up
7. #5 Add a Reproduce section to public experiment summaries
8. #3 Migrate the 2026-10-24 experiment results into the private review dataset
9. Remaining code review findings R-08–R-10 and R-13 in `experiments/` runners (no issue yet): model pinning, the no-VAD variant, runner completion checks, sweep output reuse. The second review's finding 20 (the two-track experiment summary's empty commit, malformed snapshot ID, and `git show :path` recovery command) goes with #18. The skill and recorder findings from both reviews of `5332001` merged in #20–#24; live checks not yet run: the review page's native playback in a browser and a recorder stop with one track quiet (reviewer steps in #23 and #24)
10. Build the minimal pipeline for saved recordings in `experiments/pipelines/`: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet)

## Pending

- **P-01:** open a `docs:` PR from `docs/handoff-review-fixes-merged` that removes the merged #23 and #24 subsections from `HANDOFF.md`. This branch removes them too, so P-01 is redundant if P-02's PR merges. Then delete that branch instead.
