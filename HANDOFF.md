# Handoff

## In progress

### codex/expanded-call-benchmark

- Task: the 17-recording synthetic-collection comparison, related to #28 and #11, unlinked. PR [#37](https://github.com/pomodorozhong/meeting-recap/pull/37) targets `main` at `cd2b51e` and is ready for review. It's the first summary written to the template in #39, and its decision is number 12.
- Verification on this tree: 35 pipeline, 53 synthetic-call and 116 skill tests pass, and `collection_scores.py` reproduces the committed results byte for byte. Before the last rebuild, on the same code: `collection_setup.sh` ran for real, and the `replays` step of `collection_run.sh` matched the saved words, transcripts and recaps byte for byte.
- Not run: the full `collection_run.sh` from a new folder, by the user's choice. Its other steps haven't gone through the wrapper, and hand grading wasn't repeated.
- Merging: squash with the PR's title and body, and clear the commit list GitHub pre-fills, because some commit subjects still say "expanded". This branch name and the external benchmark ID `expanded-pipeline-20261102` also keep the word.
- Next action: wait for review of #37.

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

## Ranked work

1. #28 Merge #37, then fix the remaining open PRs' wording one by one in merge order, then the private-recording pipeline review, with a public plan committed first.
2. #18 Complete the two-track listening review, freeze its reference, evaluate both runs and finish the public summary; current turn counts remain provisional.
3. #11 Publish the 17-recording synthetic recognition evidence with #37; real-call transcript accuracy remains open.
4. #1 Finish the user-confirmed long-call Who comparison; draft #25 remains open.
5. #4 Run each remaining runner and the review skill end to end on the synthetic collection, and record the results.
6. Revisit draft #31, `codex/action-grounding-sequence` and the deferred baseline and recap-accuracy branches. Keep `c714e05` reachable: the benchmark's action scoring and summary links fetch it from #31's branch.
7. #9 Choose a license.
8. #7 Decide where private experiment data is backed up.
9. #5 Extend reproducibility instructions to the remaining public summaries.
10. #3 Migrate the earlier experiment results into the private review dataset.
11. Remaining runner follow-ups: external model-cache verification, the no-VAD variant and completion checks outside the HushScribe export fix.

## Pending

- P-01 — Delete `codex/synthetic-collection-handoff`, locally and on GitHub. It only holds a stale handoff and has no PR. Needs approval because it removes a remote branch. It blocks nothing.
- P-02 — Decide draft #31: rewrite it against the 17-recording collection, or close it and keep `c714e05` reachable, for example with a tag. It blocks #31's wording pass and `codex/action-grounding-sequence`. #37 fetches `c714e05` from #31's branch.
- P-03 — Delete finished local branches: `codex/digital-silence`, `docs/main-perspective` and `docs/experiment-entry-point` now, and `stack/expanded-call-pipeline` and `codex/expanded-call-experiments` once #37 merges. It blocks nothing.
