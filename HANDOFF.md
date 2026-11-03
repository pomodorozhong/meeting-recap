# Handoff

## In progress

### docs/recognition-wording

- Task: #56, clean up stale claims and unclear wording in the experiment docs. Closes #56 through the PR body; the branch isn't linked.
- PR: none yet. Code checkpoint: `05f23d0`, on `main` at `0b1c058` (#45). Docs only.
- State: the template and writing skill say what to write when plan order or a deciding result is missing; the recognition, speakers and recaps summaries name the commits that registered their criteria instead of claiming they came before the runs; a writing-skill pass defines terms and labels numbers in the recognition and speakers summaries; decision 2's recognizer choice is marked replaced by decision 12. No result changes.
- Verification: relative links resolve, numbers in the two rewritten summaries are unchanged, `git diff --check` and a privacy scan pass. Test suites don't apply.
- Next action: open the PR once P-07 is approved.
- P-07 — Open a ready PR from `docs/recognition-wording` against `main`, titled `docs(experiments): narrow unprovable claims and define terms in the experiment docs`, with the body shown to the user on 2026-11-04. Pushing is authorized; opening a PR is not. It blocks closing #56.

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

1. #46 Run Turbo through the pause option's acceptance check (P1, on `feat/turbo-pause-check`).
2. #28 Run the private-recording pipeline review, with a public plan committed first.
3. #18 Complete the two-track listening review, freeze its reference, evaluate both runs and finish the public summary; current turn counts remain provisional.
4. #11 Compare real-call transcript accuracy; the synthetic evidence is on `main`.
5. #1 Finish the user-confirmed long-call Who comparison; draft #25 remains open.
6. #47 Grade a recap on a long meeting.
7. #49 Score label attachment on Turbo's text. Should need no new model runs.
8. #51 Add the `replays` results to the scorer and results file.
9. #52 Run the collection entry point end to end on a fresh folder. `collection_run.sh` hasn't been run whole from a new folder.
10. #57 Add synthetic noisy calls to the test collection.
11. #53 Warn when a recording's language looks wrong for `--language`.
12. #54 Reconcile the recognizer memory figures across reports.
13. #55 Separate temperature from word timestamps in the recognition baseline.
14. #48 Separate Turbo from Who in the recap comparison.
15. #50 Test `--keep-asr-segments` with full Whisper and Sortformer.
16. #56 Clean up claims and stale text in the experiment docs: built on `docs/recognition-wording`, waiting on P-07.
17. #4 Run each remaining runner and the review skill end to end on the synthetic collection, and record the results.
18. Revisit draft #31, `codex/action-grounding-sequence` and the deferred baseline and recap-accuracy branches. Keep `c714e05` and `d182e52` reachable: the merged summaries link to them, on #31's branch and `codex/expanded-call-benchmark`. The latter's commits also show when each criterion's text was registered.
19. #9 Choose a license.
20. #7 Decide where private experiment data is backed up.
21. #5 Extend reproducibility instructions to the remaining public summaries.
22. #3 Migrate the earlier experiment results into the private review dataset.
23. Remaining runner follow-ups: external model-cache verification, the no-VAD variant and completion checks outside the HushScribe export fix.

## Pending

- P-02 — Decide draft #31: rewrite it against the 17-recording collection, or close it and keep `c714e05` reachable, for example with a tag. The action comparison left out of #37's split belongs with this decision. It blocks #31's wording pass and `codex/action-grounding-sequence`. Checked 2026-11-03: it conflicts with `main` in 10 files and its pipeline options and runners have merged in other forms. What only it holds is the action-recovery work. Recommended: tag `c714e05`, close it, and file an issue for action recovery.
