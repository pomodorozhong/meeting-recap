# Handoff

## In progress

### codex/meeting-experiment-review

- Task: project foundation: experiment review skill, runners, experiment records, tests (advances #2; closes #6)
- PR: [#10](https://github.com/pomodorozhong/meeting-recap/pull/10), awaiting review and merge
- Code checkpoint: 8c39d42
- State: complete for review. The skill, runners, docs, and tests are in. The private dataset (`$MEETING_REVIEW_DATA`) holds both full recordings, 10 runs (Sortformer, Whisper and Breeze through MLX, and their attached runs), an unanswered review session, and a code snapshot for 2026-10-29.
- Verification: 67 tests in `tests/skill/` pass (command in AGENTS.md); `dataset.py validate "$MEETING_REVIEW_DATA"` passes; every branch commit scanned for names, transcript text, and private paths.
- Next action: after review, squash-merge #10, then remove this subsection.
- Avoid: naming a skill script after a standard-library module (`select.py` crashed the review server); the rabbit-holes default branch is `master`, not `main`.
- Pending: **P-04** merge #10. Why: merging needs approval. Blocks: everything building on the skill and docs.

## Ranked work

1. #8 Decide the repository layout for the pipeline and app (blocks pipeline code)
2. #9 Choose a license
3. #7 Decide where private experiment data is backed up
4. #4 Add a shareable synthetic test recording
5. #5 Add a Reproduce section to public experiment summaries
6. #3 Migrate the 2026-10-24 experiment results into the private review dataset
7. Build the minimal pipeline for saved recordings: ASR and Sortformer, attachment, naming, Markdown transcript (no issue yet; after #8)
8. #1 Evaluate Desert Ant Labs Who for on-device speaker diarization

## Pending

- **P-01** File issue: "Compare Breeze-ASR-25 and Whisper Large v3 transcript accuracy". Labels: `enhancement`. Body: Breeze-ASR-25 through MLX is fast enough (about 0.25× real time, see the transcription summary's 2026-10-29 follow-up) and writes Traditional characters, but whether its text is more accurate than Whisper Large v3 (Chinese forced) on a three-person Chinese + English call is untested. Register a new experiment from `docs/experiments/TEMPLATE.md` before running: short (5–10 s) transcript clips where the two disagree plus typical clips, chosen with `pick_clips.py`; the user types what they hear; compare exact wording, dropped or invented words, names, and English terms. The MLX transcription and Sortformer runs of both full recordings are already in the private dataset and can be reused. Done when the summary states which model the pipeline uses and why.
  Why: filing issues needs approval. Blocks: choosing the pipeline's ASR model.
- **P-02** Change [rabbit-holes#226](https://github.com/pomodorozhong/rabbit-holes/pull/226) from "Refs #194" to "Closes #194", so the phase 3 issue closes when the research topic's conclusion merges.
  Why: editing a PR in another repository needs approval. Blocks: closing rabbit-holes#194.
- **P-03** Close [#2](https://github.com/pomodorozhong/meeting-recap/issues/2) when #10 merges, or keep it open until #3 brings in the 2026-10-24 evidence (see the [handoff note](https://github.com/pomodorozhong/meeting-recap/issues/2#issuecomment-6490857300)).
  Why: a decision about issue scope. Blocks: nothing.
