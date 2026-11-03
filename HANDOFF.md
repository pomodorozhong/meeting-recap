# Handoff

## In progress

### docs/experiment-writing-skill

- Task: add the `experiment-writing` skill for experiment summaries and decisions. Unlinked. It holds two references: `writing-principles.md`, copied from `rabbit-holes`, and `experiment-summaries.md`, written for this repository.
- Verification: its links resolve. It was tried on #43 and #44 by the session that wrote it, so it hasn't had a cold test by a fresh session.
- Related work: #43 and #44 hold the last two summaries split from #37. Merge #43 first, then #44, and rebuild the remaining PR after each merge. `docs/recognition-wording` holds plain-language fixes for the merged recognition summary, and its PR waits until those two merge and the wording fixes are complete.
- Keep `codex/expanded-call-benchmark`: its commits show when each criterion was registered, and the recaps summary links to its action results at `d182e52`.
- Next action: wait for review of this PR.

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

## Ranked work

1. #28 Merge the writing skill, then #43 and #44, then the recognition wording PR, then the private-recording pipeline review, with a public plan committed first.
2. #18 Complete the two-track listening review, freeze its reference, evaluate both runs and finish the public summary; current turn counts remain provisional.
3. #11 Publish the 17-recording synthetic recognition evidence with `docs/collection-recognition`; real-call transcript accuracy remains open.
4. #1 Finish the user-confirmed long-call Who comparison; draft #25 remains open.
5. #4 Run each remaining runner and the review skill end to end on the synthetic collection, and record the results.
6. Revisit draft #31, `codex/action-grounding-sequence` and the deferred baseline and recap-accuracy branches. Keep `c714e05` reachable: the synthetic-collection summaries link to it on #31's branch. The runner no longer needs it.
7. #9 Choose a license.
8. #7 Decide where private experiment data is backed up.
9. #5 Extend reproducibility instructions to the remaining public summaries.
10. #3 Migrate the earlier experiment results into the private review dataset.
11. Remaining runner follow-ups: external model-cache verification, the no-VAD variant and completion checks outside the HushScribe export fix.

## Pending

- P-01 — Delete `codex/synthetic-collection-handoff`, locally and on GitHub. It only holds a stale handoff and has no PR. Needs approval because it removes a remote branch. It blocks nothing.
- P-02 — Decide draft #31: rewrite it against the 17-recording collection, or close it and keep `c714e05` reachable, for example with a tag. The action comparison left out of #37's split belongs with this decision. It blocks #31's wording pass and `codex/action-grounding-sequence`.
- P-03 — Delete finished local branches: `codex/digital-silence`, `docs/main-perspective` and `docs/experiment-entry-point` now, and `stack/expanded-call-pipeline` and `codex/expanded-call-experiments` once the split merges. It blocks nothing.
