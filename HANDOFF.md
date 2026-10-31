# Handoff

## In progress

### feat/saved-audio-pipeline

- Task: #28, the first saved-audio to Markdown pipeline. Plan approved 2026-11-01, using Qwen3.5 9B through MLX for the recap and never Ollama: if MLX breaks, stop and ask. The private-recording trial goes in a later PR. The branch is local and unlinked; its PR will say `Related to #28`.
- Code checkpoint: `c790c5b` plus this handoff commit; pushed to `origin/feat/saved-audio-pipeline`, no PR yet.
- State: `experiments/pipelines/whisper-sortformer/` runs convert → MLX Whisper → Sortformer → attach → speaker mapping → transcript → recap. The synthetic call ran end to end in 283 s for 5:29 of audio, with 6.71 GB MLX peak. Transcript speaker agreement is 95.1% (diarization alone 98.2%). The ranked issues are in that folder's README; the top one is words crossing turn boundaries.
- Verification: 22 pipeline tests pass (generated audio, fake model stages). Real `setup`, `run`, `render` with a merge, `summarize` refusal and `summarize --replace` were run on the synthetic call.
- Next action: resolve P-01, then a public experiment plan in `docs/experiments/` before running on one private recording with the `meeting-experiment-review` skill. That run reviews transcript usefulness, speaker correction effort, and recap support and omissions.
- P-01 — Awaiting approval to open a ready PR from `feat/saved-audio-pipeline` against `main`, titled `feat(pipelines): add a saved-audio to Markdown transcript and recap pipeline`, with the exact body below. The open-pr skill requires approval of the finished branch and body; opening a PR needs the user's approval even though pushing does not.

#### P-01 proposed PR body

```markdown
## What changed

- Add `experiments/pipelines/whisper-sortformer/`, the first end-to-end pipeline for a saved recording. `recap.py run AUDIO OUT` converts the audio with ffmpeg, runs Whisper Large v3 through MLX (Chinese forced, word timestamps), runs FluidAudio Sortformer, attaches labels per word by overlap, and writes `transcript.md`: Traditional Chinese with `[HH:MM:SS] Speaker` turns. It then writes `summary.md` from Qwen3.5 9B 4-bit through `mlx-lm`, with topics, decisions, action items, proposals and open questions, each citing transcript timestamps.
- `speakers.json` maps labels to names, defaulting to Speaker A/B/C. `recap.py render OUT` applies renames and merges without rerunning ASR or diarization. `summarize OUT --replace` rewrites the recap with the new names.
- **Runs:**
  - Models load in their own processes, one at a time.
  - Every stage records wall time, peak RSS and footprint (plus MLX's own peak for MLX stages) and output digests in `stages.json`.
  - A failed stage reports itself, keeps completed outputs and resumes with `--resume`.
  - Existing output folders, folders inside the checkout, and an existing `summary.md` are refused unless explicitly allowed.
  - `fluidaudiocli` exits 0 on failure, so the pipeline checks its output file instead.
- **Setup:** `recap.py setup` downloads the pinned snapshots and FluidAudio's models once; ordinary runs set `HF_HUB_OFFLINE=1`.
- **Pins:** Whisper `49e6aa2…`, Qwen3.5 `8b2b98c…`, FluidAudio `ea50062…`, plus a uv lock.
- **Recap evidence:** cited timestamps that don't start a transcript line are dropped, and unsupported items are marked.
- The pipeline README records the synthetic-call baseline and the issues it found, most important first. Decision 7 records the MLX-only recap model. The status page, runner guide and handoff point to the pipeline.

## Why

The project had component scores but no pipeline that turns a recording into notes. Without one, it was unclear which problems matter most end to end. This baseline shows where the pipeline loses most.

On the synthetic call (5:29, three speakers):
- **Runtime:** 283 s in all (0.86× real time). Sortformer took 136 s and Whisper 47 s.
- **Memory:** 6.71 GB peak, from the recap model.
- **Speaker agreement:** diarization alone agrees on 98.2% of characters, but the transcript agrees on only 95.1% once text is aligned to the script. Whisper's word times push the start of replies into the previous turn.

That boundary drift ranks first, ahead of recap structure, Sortformer runtime, and ASR or punctuation errors.

## Verification

### Automated checks

- `uv run --project experiments/pipelines/whisper-sortformer python -m unittest discover -s tests/pipelines -t tests/pipelines`: 22 tests pass, also on the feature commit alone in a clean worktree. They cover per-word attachment and turn joining, rename and merge, Markdown, chunking, recap parsing and evidence checks, failure records, resume without rerunning completed stages, refusing a different recording, and refusing to replace outputs. They use generated audio with fake model stages.
- `uv run --no-project --with opencc-python-reimplemented python -m unittest discover -s tests/skill -t tests/skill`: 116 tests pass.
- `uv run --no-project python -m unittest discover -s tests/experiments`: 10 tests pass.
- `uv lock --check --project experiments/pipelines/whisper-sortformer`: passes.
- `git diff --check` and a scan of new files for private paths and names: pass.
- Not run: any private recording. That trial and its listening review follow in a later PR, with its public plan committed first.

### How to verify

1. Run the setup in the pipeline README: `swift build -c release --product fluidaudiocli` in the folder, then `recap.py setup`. Generate the synthetic call with `experiments/synthetic-call/generate.py`.
2. `uv run --project experiments/pipelines/whisper-sortformer experiments/pipelines/whisper-sortformer/recap.py run experiments/synthetic-call/out/script/call.wav <new folder outside the checkout>`. Expected: every stage completes in about 5 minutes and `transcript.md`, `summary.md`, `speakers.json` and `stages.json` appear.
3. Give `Speaker_3` the same name as `Speaker_2` in `speakers.json` and run `recap.py render <folder>`. Expected: no `Speaker D` in `transcript.md`, and a note that `summary.md` used earlier names.
4. Run `recap.py summarize <folder>`. Expected: it refuses and `stages.json` still shows the summary as completed. With `--replace`, it writes a new recap.

Verified: steps 1–4 on an M2 Pro with 16 GB, macOS 26.6.2. Reviewer follow-up: none required. The private-recording review is planned separately.

## Related issues

Related to #28: delivers the transcript checkpoint, speaker mapping, local recap, synthetic-call run, generated-data checks and setup and runtime docs. The private-recording trial and its review are still to do, so the issue stays open.
Related to #11: the pipeline starts from Whisper Large v3 without waiting for that comparison.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Ranked work

1. #28 First saved-audio to Markdown pipeline: built on `feat/saved-audio-pipeline` (see its section above); the private-recording trial and review remain
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
