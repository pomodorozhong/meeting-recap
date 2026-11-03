# Handoff

## In progress

### codex/digital-silence

- Task: digital silence and long mute handling for the pipeline, related to #28 and unlinked. Rebuilt on `main` at `9fa2903` from the stack's `3d254b6`. The only conflicts were with #35's option, in `recap.py` and the README. Pushed; no PR yet.
- Verification: 35 pipeline tests pass. On the stacked benchmark branch, whose pipeline code matches apart from `compare_lines.py`: the silence control skipped ASR and the recap, the onboarding split replay matched all 274 saved words and times, and the English Turbo replay matched the graded transcript byte for byte. Swift binaries were not rebuilt because the packages are unchanged.
- Next action: resolve P-01.
- P-01 — Awaiting approval to open a ready PR from `codex/digital-silence` against `main`, titled `fix(pipeline): handle digital silence and long mutes`, with the exact body below. Pushing is authorized; opening a PR is not.

#### P-01 proposed PR body

````markdown
## What changed

- A recording whose converted samples are all exactly zero now skips Whisper and the recap model. `asr.json` and `summary.json` record `skipped: digital_silence`, the transcript is empty, and `summary.md` says the recording is digitally silent. The diarizer still runs.
- Add `--split-digital-pauses`, off by default and for full Whisper only. It decodes the speech on each side of a run of at least five seconds of exact zero, keeps 250 ms of context, and restores timestamps relative to the original recording. `run` refuses it with `--asr turbo-q4`, and `--resume` refuses a changed setting.
- `asr.json` now records `settings.digital_pauses` and `spans_samples`, and `run.json` records `split_digital_pauses`.
- The ASR stage now reads the converted WAV itself, so `scipy` becomes a direct dependency of the pipeline's uv project. It refuses an empty file or anything other than 16 kHz mono.

## Why

Without a check, Whisper can hallucinate text on silence, and the recap then summarizes text nobody said. A long digital mute inside a call also damages recognition: on the synthetic onboarding call, full Whisper made 91 edits when decoding the whole file and 11 when split at the pause.

The rule only looks at exact digital zero, so it isn't a voice activity detector. Quiet but nonzero audio decodes as before.

## Verification

### Automated checks

- `uv run --project experiments/pipelines/whisper-sortformer python -m unittest discover -s tests/pipelines -t tests/pipelines`: 35 tests pass, including new ones for all-zero input, a quiet nonzero signal, and word times after a split.
- `uv lock --project experiments/pipelines/whisper-sortformer --check`: current.
- Not run: `swift build`. This PR doesn't change the Swift packages, so the replays used binaries already built from the same `Package.resolved`.
- Not run: the recap on non-silent input. The onboarding and English replays used `--no-summary`.

### How to verify

Set `FIXTURES` to the verified seventeen-recording collection from `experiments/synthetic-call/`, set `P=experiments/pipelines/whisper-sortformer`, and use a new output folder for each run.

1. `uv run --project "$P" "$P/recap.py" run "$FIXTURES/silence/call.wav" "$OUT" --diarizer who`
   Expected: `asr.json` and `summary.json` both say `skipped: digital_silence`, and `summary.md` says the recording is digitally silent.
2. `uv run --project "$P" "$P/recap.py" run "$FIXTURES/onboarding/call.wav" "$OUT" --diarizer who --split-digital-pauses --no-summary`
   Expected: `asr.json` has two `spans_samples` and 274 words.
3. `uv run --project "$P" "$P/recap.py" run "$FIXTURES/english-audit/call.wav" "$OUT" --diarizer who --asr turbo-q4 --language en --keep-asr-segments --no-summary`
   Expected: the run completes with the options merged in #33, #34 and #35 still working alongside this change.

Verified: steps 1 to 3 on an M2 Pro with 16 GB. They ran on the stacked benchmark branch, whose pipeline code is identical to this branch apart from a separate helper script. In step 2, all 274 words and their times matched the saved experiment output. In step 3, the transcript matched the graded one byte for byte. Reviewer follow-up: none required.

## Stack

1. **Digital silence and mutes (this PR).** Independent; it targets `main` on its own.
2. Expanded call benchmark. It must merge after this PR.

## Related issues

Related to #28: handles silent and muted saved recordings. The issue stays open for the private-recording review.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
````

### feat/pipeline-baseline

- Saved synthetic-call runs of the pipeline; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

### feat/recap-accuracy

- Recap accuracy check and summary-stage variants; to be rebuilt on `main`, and deferred by the user. Read that branch's own `HANDOFF.md`.

## Ranked work

1. #28 Merge the digital-silence and expanded benchmark PRs, then the private-recording pipeline review, with a public plan committed first. The language, Turbo and citation-line options merged in #33, #34 and #35.
2. #18 Complete the two-track listening review, freeze its reference, evaluate both runs and finish the public summary; current turn counts remain provisional.
3. #11 Publish the expanded synthetic recognition evidence with the benchmark; real-call transcript accuracy remains open.
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
