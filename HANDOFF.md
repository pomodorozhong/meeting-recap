# Handoff

## In progress

### docs/experiment-writing-skill

- Task: add the `experiment-writing` skill for experiment summaries and decisions. Related to #28, unlinked. PR [#45](https://github.com/pomodorozhong/meeting-recap/pull/45) is ready for review. It holds `writing-principles.md`, copied from `rabbit-holes`, and `experiment-summaries.md`, written for this repository. There's no `AGENTS.md` pointer or template change, by the user's choice.
- Code checkpoint: `02adc8c` plus the handoff commits, pushed.
- Verification: its links resolve. The session that wrote it tried it on #43 and #44, and that found real problems, but it hasn't had a cold test.
- Next action: run the cold test. The user will start a new session that rewrites the silence summary from #43 using only the skill and the experiment's results, on a local branch. Then compare that rewrite with #43, and use the differences to decide what changes in #43, #44 and this skill.
- Related work:
  - Hold #43 and #44 until that comparison. Then merge #43, then #44.
  - After #43 merges, rebase #44 on `main`. The only conflicts are in `docs/decisions.md` and the experiments index: keep both entries, in numeric order.
  - `docs/recognition-wording` (`fe9ae7a`, pushed, no PR) holds plain-language fixes for the merged recognition summary. Its PR comes last, after running the skill over the merged #41 and #42 summaries and adding those fixes.
- Keep `codex/expanded-call-benchmark`: its commits show when each criterion was registered, and the recaps summary links to its action results at `d182e52`.
- Local only: the worktree `.claude/worktrees/collection-split`, `stack/collection-split`, the `refs/propose-stack/collection-split/*` refs and the working files in `.agents/propose-stack/`. None is needed to resume. Delete them after the split merges, with the user's approval.

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

## Ranked work

1. #28 Run the writing skill's cold test, then merge #45, #43 and #44, then open the recognition wording PR, then the private-recording pipeline review, with a public plan committed first.
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
- P-04 — Two wording changes the user hasn't answered, because they chose the cold test instead: reword how #43 describes checking the pause option and why it supports only full Whisper, and add a rule to the skill in #45 about naming who did something and not writing "because" unless the source gives that reason. Revisit after the cold test, which may make them unnecessary. It blocks nothing else.
