# Handoff

## In progress

### docs/main-perspective

- Task: correct docs on `main` that describe work as if a reader could see unmerged branches or earlier drafts. Unlinked. Branch from `main` at `2e9c901`.
- Verification: pipeline and synthetic-call tests pass. The only code change is one `recap.py` help string.
- Next action: wait for review. #37 must be rebuilt on `main` after this merges.

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

## Ranked work

1. #28 Merge the docs correction PR, then #37, then the private-recording pipeline review, with a public plan committed first. The language, Turbo, citation-line and digital-silence changes merged in #33, #34, #35 and #36.
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

None.
