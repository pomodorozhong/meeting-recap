# Handoff

## In progress

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

### feat/turbo-pause-check

- Task: #46, run Turbo through the pause option's acceptance check. Linked to #46, so its PR closes that issue.
- PR: none yet. Code checkpoint: `88236e8` on `main`. Not started; this branch only holds the handoff so far.
- Verification: none run on this branch.
- Before running: `recap.py` and `asr_stage.py` refuse `--split-digital-pauses` with `--asr turbo-q4`, and a test expects that, so this needs a code change. Commit the experiment's summary before its first run, and use synthetic audio only.
- Next action: draft the experiment's summary from `docs/experiments/TEMPLATE.md`, then allow the flag with Turbo and run it on `onboarding`.

## Ranked work

1. #44 Rebuild `docs/collection-recaps` on `main`, since it adds to the same lines of `docs/decisions.md` and the experiments index as #43, then merge it.
2. #46 Run Turbo through the pause option's acceptance check (P1, on `feat/turbo-pause-check`).
3. #28 Run the private-recording pipeline review, with a public plan committed first.
4. #18 Complete the two-track listening review, freeze its reference, evaluate both runs and finish the public summary; current turn counts remain provisional.
5. #11 Compare real-call transcript accuracy; the synthetic evidence is on `main`.
6. #1 Finish the user-confirmed long-call Who comparison; draft #25 remains open.
7. #47 Grade a recap on a long meeting.
8. #49 Score label attachment on Turbo's text. Should need no new model runs.
9. #51 Add the `replays` results to the scorer and results file.
10. #52 Run the collection entry point end to end on a fresh folder. `collection_run.sh` hasn't been run whole from a new folder.
11. #57 Add synthetic noisy calls to the test collection.
12. #53 Warn when a recording's language looks wrong for `--language`.
13. #54 Reconcile the recognizer memory figures across reports.
14. #55 Separate temperature from word timestamps in the recognition baseline.
15. #48 Separate Turbo from Who in the recap comparison. Depends on #44.
16. #50 Test `--keep-asr-segments` with full Whisper and Sortformer. Depends on #44.
17. #56 Clean up claims and stale text in the experiment docs. Check against `docs/recognition-wording` first.
18. #4 Run each remaining runner and the review skill end to end on the synthetic collection, and record the results.
19. Revisit draft #31, `codex/action-grounding-sequence` and the deferred baseline and recap-accuracy branches. Keep `c714e05` and `d182e52` reachable: the merged summaries link to them, on #31's branch and `codex/expanded-call-benchmark`. The latter's commits also show when each criterion's text was registered.
20. #9 Choose a license.
21. #7 Decide where private experiment data is backed up.
22. #5 Extend reproducibility instructions to the remaining public summaries.
23. #3 Migrate the earlier experiment results into the private review dataset.
24. Remaining runner follow-ups: external model-cache verification, the no-VAD variant and completion checks outside the HushScribe export fix.

## Pending

- P-01 — Delete `codex/synthetic-collection-handoff`, locally and on GitHub. It only holds a stale handoff and has no PR. Needs approval because it removes a remote branch. It blocks nothing.
- P-02 — Decide draft #31: rewrite it against the 17-recording collection, or close it and keep `c714e05` reachable, for example with a tag. The action comparison left out of #37's split belongs with this decision. It blocks #31's wording pass and `codex/action-grounding-sequence`.
- P-03 — Delete finished local branches: `codex/digital-silence`, `docs/main-perspective` and `docs/experiment-entry-point` now, and `stack/expanded-call-pipeline` and `codex/expanded-call-experiments` once the split merges. It blocks nothing.
- P-04 — Delete the local branches `docs/silence-cold-rewrite` and `docs/collection-silence`. #43 merged at `88236e8` with identical content, and its remote branch is already gone. It blocks nothing.
- P-05 — Post the cold test's findings on #45, or fold them into its skill. Needs approval because the task ruled out commenting on PRs. It blocks nothing, but #45 shouldn't merge without considering them.
  - Helped: checking sources before rewording, how each test came about, describing only procedures that exist, what the numbers count, and cold read item 4.
  - Unclear: planned tests on recordings whose failure was already known; the template's "the result that decided it" against the cold read's "say the choice is cautious"; how far an added cause or caution may go.
  - Missing: numbers that exist only in prose, not the results file; verifying commands that can't be run; how much commit history belongs in a summary, and leaving it out when the order can't be established; sibling documents repeating a weakened claim; where to record a problem with a decision you may not change.
