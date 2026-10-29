---
name: meeting-experiment-review
description: Run local speech experiments (transcription, speaker diarization, label attachment) on private meeting recordings, collect the user's listening judgments in a local review page, and score runs against confirmed references. Use when comparing ASR or diarization models or settings on a real recording, preparing clips for the user to listen to, recording what the user heard, or evaluating speaker separation without a hand-made reference transcript.
---

# Meeting Experiment Review

Recordings, transcripts, and the user's answers are private. Every artifact lives in a **private dataset directory outside any Git checkout**; the scripts refuse to create one inside a repository. Never copy audio, transcript text, speaker names, or answers into a repo, issue, PR, commit, or chat summary beyond what the user asks for. The only output that goes into a repository is the public summary in step 6.

All helpers are standard-library Python 3.11+ in `scripts/`. Run them as `python3 <skill>/scripts/<name>.py`. Every command prints JSON; failures exit nonzero with a one-line reason.

## Ground rules

- **Artifacts are immutable.** Recordings, runs, sessions, references, and evaluations are written once with SHA-256 digests. To change a prediction, register a new run ID; never edit files inside the dataset by hand. `dataset.py validate` detects changes.
- **Only the user confirms ground truth.** Answers come from the review page or from a JSON file holding exactly what the user said. Never fill in a `confirmed` answer from a model output, a participant list, or your own guess. If the user is unsure, record `unsure`.
- **Keep claims inside the evidence.** The evaluation measures speaker turn order on selected clips. It is not DER, not transcript accuracy, and not an error rate for the whole recording. Say so when reporting.
- **Code is frozen per experiment.** `review.py prepare` and `reference`, `evaluate.py`, `attach.py`, and `pick_clips.py` copy the skill's scripts and page into `<dataset>/code/<sha256>/` (once per version) and record that ID and the Git commit in what they write. To redo a step of an old experiment exactly, run the script from its snapshot, for example `python3 <dataset>/code/<sha256>/scripts/pick_clips.py …`. So the live scripts never need options kept only to reproduce old experiments; remove them instead. `python3 scripts/dataset.py snapshot <dataset>` takes a snapshot on demand.
- **Compare like with like.** One evaluation covers runs on the same recording and the same reference clips; the script rejects anything else.

## Workflow

### 0. Register the experiment in the repository before any run

Copy `docs/experiments/TEMPLATE.md` to `docs/experiments/YYYY-MM-DD-<topic>.md`, fill in everything above **Runtime and memory**, add it to `docs/experiments/README.md`, and commit it before the first run. It is the public summary from then on; step 6 completes it. It must state:

- the question, the decision it informs, the experiments it builds on, the assumptions (input, models, machine), and the expected result, so the experiment can be restarted if private data is lost;
- the input profile, never its name or path;
- the planned run IDs with pinned models, settings, and commands; the `pick_clips.py` config; and the session, reference, and evaluation IDs, chosen now;
- the exact command that starts the review server, so the user can run it without an agent:

  ```bash
  python3 .agents/skills/meeting-experiment-review/scripts/review.py serve "$MEETING_REVIEW_DATA" --session <session-id> --port 8770
  ```

  Use the `$MEETING_REVIEW_DATA` variable, never the dataset path. Tell the user to set it in their shell profile if it is not set.

Commit it under the same privacy rules as the final summary. When the plan changes during the experiment (another run, a different config), update the file and commit again before acting on the change, and say why in the file.

### 1. Create the dataset and add recordings

```bash
python3 scripts/dataset.py init ~/Documents/meeting-review-data
ffprobe -v error -show_entries format=duration -of csv=p=0 call-part1.mp4
python3 scripts/dataset.py add-recording ~/Documents/meeting-review-data --id part1 --audio call-part1.mp4 --duration 1343.317 --group call-2026-10-22
```

Register the **original, browser-playable media** (MP4, M4A, MP3), not a converted float WAV: the review page plays the registered file, and browsers do not reliably play 32-bit float WAV. Models usually want 16 kHz mono WAV; convert a scratch copy with `ffmpeg -i in.mp4 -ac 1 -ar 16000 -c:a pcm_f32le out.wav` for the runners. The conversion keeps the time origin, so run timestamps line up with the registered media. Parts of one call share a `--group`. The media is copied into the dataset.

### 2. Produce and register runs

Runs can come from any tool that writes the formats in [references/formats.md](references/formats.md); this repository's runners are described in `docs/runners.md`. Write raw output to a scratch directory, then register each output with a run spec:

```json
{"id": "sortformer-part1", "recording_id": "part1", "model": "fluidaudio-sortformer",
 "status": "completed", "artifacts": {"segments": "sortformer_seg.json", "raw": "sortformer.json"},
 "config": {"fluidaudio": "ea50062…", "input": "16 kHz mono WAV from source.mp4"},
 "runtime": {"wall_seconds": 721, "peak_rss_mb": 1061, "host": "M2 Pro 16 GB"}, "notes": ""}
```

```bash
python3 scripts/dataset.py add-run ~/Documents/meeting-review-data --spec run.json
```

- Artifact paths are relative to the spec file. Use `segments` for diarization output and `transcript` for WhisperKit-shaped ASR JSON; other names (such as `raw`) are stored but not read.
- Put pinned versions and every non-default setting in `config`; the public summary is written from it.
- Measure wall time and peak memory with `/usr/bin/time -l`. Runs that share the machine slow each other down; run timed jobs one at a time, or say in `notes` which runs overlapped.
- Record failed or partial runs too, with `status` `failed` or `incomplete`.

To label transcript text with diarization speakers, derive a new run:

```bash
python3 scripts/attach.py ~/Documents/meeting-review-data --asr-run whisper-part1 --diarization-run sortformer-part1 --id whisper-sortformer-part1 --method word
```

`word` (default) needs word timestamps; `seg` attaches whole ASR segments by overlap; `line` reproduces HushScribe's single-point lookup for comparison.

### 3. Choose clips and prepare a session

Pick clips that answer the user's question and give each a reason:

- **Speaker order:** windows of 10–15 s starting a few seconds before a predicted turn change, spread across the recording (for example one per equal time bin), plus places where runs disagree, overlaps, short interjections, and rarely used labels (a voice split across two labels shows up there).
- **Transcript:** windows where runs disagree most, plus one or two typical windows so the comparison is fair. Normalize script first (OpenCC `s2tw`) so Simplified vs. Traditional differences do not dominate. Keep these clips short (5–10 s): the user has to type what they hear.
- Skip ranges the user already reviewed in an earlier session unless you are checking repeatability.
- Keep the session to what one sitting allows (about 10–20 items).

`scripts/pick_clips.py` applies the speaker-order and transcript rules above from registered runs, with a fixed seed, and writes a plan. It needs OpenCC for transcript clips, so run it with `uv run`:

```json
{"id": "full-calls-2026-10-29", "question": "Does Sortformer keep the speakers apart?", "seed": 20261029,
 "recordings": [{"recording_id": "part1", "skip_before": 600,
                 "diarization_run": "sortformer-part1", "speaker_clips": 4,
                 "speaker_show_runs": ["sortformer-part1", "whisper-sortformer-part1"],
                 "transcript_runs": ["whisper-mlx-part1", "breeze-mlx-part1"], "transcript_clips": 2}]}
```

```bash
uv run scripts/pick_clips.py ~/Documents/meeting-review-data --config select.json --out plan.json
```

Optional keys and defaults: `window_seconds` 15, `lead_seconds` 4, `min_overlap` 0.3, `min_turns` 2, `max_turns` 5, `min_gap_seconds` 20, `transcript_gap_seconds` 60, `min_characters` 30, `normalize` `both` (`first` converts only the first transcript run, as the 2026-10-29 session did). Save the config next to the private report so the selection can be rerun; the plan records it under `selector.method`. If a time bin has no turn-change window that avoids the other clips, or there are too few transcript windows far enough apart, the plan has fewer items than asked and the command prints them under `shortfall` (also kept in `selector.shortfall`). A bin crowded by an earlier pick still gets a clip, as long as it does not overlap one. Review the plan and add or replace items by hand when the question needs clips the rules miss.

A hand-written plan records how the clips were chosen in `selector` (extra fields such as `method` and `seed` are kept):

```json
{"id": "turns-part1", "question": "Which diarizer keeps three speakers apart?",
 "selector": {"name": "agent-selected", "version": "1", "seed": 20261029, "method": "one 15 s window per time bin…"},
 "items": [{"id": "c01", "task": "speaker_order", "recording_id": "part1",
            "start_seconds": 312.0, "end_seconds": 327.0, "padding_seconds": 1,
            "reason": "Runs disagree on a quick hand-off", "run_ids": ["sortformer-part1", "community1-part1"]}]}
```

`task` is `speaker_order` (who speaks, in order) or `transcript` (what was said). `run_ids` choose which predictions the page can show next to the clip.

```bash
python3 scripts/review.py prepare ~/Documents/meeting-review-data --plan plan.json
```

### 4. Collect the user's answers

```bash
python3 scripts/review.py serve ~/Documents/meeting-review-data --session turns-part1 --port 8770
```

- Run it in the background and give the user the printed `http://127.0.0.1:…/?token=…` URL (opening it in the built-in browser pane works). Do not log or repeat the token elsewhere.
- The server serves `assets/review.html` from the skill on each request, so moving or editing the skill breaks a running server. Restarting prints a new token; saved answers are kept.
- Before the user starts, tell them to use the same speaker IDs for each person throughout (names or initials); these become the reference. Names stay in the dataset.
- For a transcript clip that is too long to type, the user can save `unsure` and say in the feedback which run is closer. That answer is not a reference, but it can be reported as a preference.
- The page plays each clip, can reveal predictions, and saves answers and text notes to the dataset. Stop the server when the user finishes.

If the user answers in chat instead, write their exact answer to a JSON file outside the repo and save it:

```json
{"item_id": "c01", "state": "confirmed", "annotation": {"speaker_order": ["A", "B", "A"]}, "feedback_text": ""}
```

```bash
python3 scripts/review.py answer ~/Documents/meeting-review-data --session turns-part1 --file answer.json
```

States are `confirmed`, `unsure`, `skipped`, `unusable`. A confirmed `speaker_order` needs an explicit list (empty for no speech); set `"allow_extra_turns": true` when the user says brief extra turns are acceptable. A confirmed `transcript` needs `text`.

### 5. Freeze a reference and evaluate

```bash
python3 scripts/review.py close ~/Documents/meeting-review-data --session turns-part1
python3 scripts/review.py reference ~/Documents/meeting-review-data --session turns-part1 --id ref-part1
python3 scripts/evaluate.py ~/Documents/meeting-review-data --reference ref-part1 --runs sortformer-part1 community1-part1 --id eval-part1
```

- The reference keeps only confirmed items and lists the rest as excluded.
- `evaluate.py` scores `speaker_order` items only, one recording per evaluation; run it once per recording. It writes `evaluations/<id>/evaluation.json` and `report.md` with turns recovered and clips correct per run.
- By default each run's labels are mapped to people in whichever way scores best, which flatters runs; pass `--mappings mappings.json` (`{"run-id": {"label": "A"}}`) to test a fixed naming. Only completed runs can be scored.
- Confirmed `transcript` items are not scored by a script. Compare them with each run's text yourself in the private report (exact wording, dropped or invented words, names and terms).

### 6. Report in two parts

**Full report, private:** `<dataset>/reports/<id>.md`, where `<id>` matches the session or evaluation. It may include names, quoted transcript text, and timestamps. Link the session, reference, and evaluation IDs and the run IDs it draws on. Cover per-clip results, what the user heard that the scores miss, and transcript comparisons. Create the `reports/` folder if needed. Unlike the dataset's other artifacts, reports are prose and may be revised; the evaluation and reference files they cite stay fixed.

**Public summary, in the repository:** complete the file registered in step 0. Set its status, and fill in:

- runtime and peak memory per run, with any overlap noted;
- scores, excluded-item count, and mapping method;
- the metric's limits;
- the decision, and open questions;
- any departure from the plan and why.

It must never contain participant names, transcript text, audio paths, or dataset paths. Refer to people as Speaker A/B/C and to recordings by duration. Before committing, grep the summary for every participant name and for a few distinctive transcript phrases.

In both, lead with the decision the user asked about, separate what was measured from what was only listened to, and keep anything unresolved as an open question. If the listening review is still pending, write the run results into both now, set the status to `review pending`, and commit; update both once the review finishes.

## Other checks

`python3 scripts/dataset.py validate <dataset>` rechecks every digest and the event logs.

This repository tests every script in `tests/skill/` (see AGENTS.md for the command). Run the tests after changing the skill, and add tests for new behavior. Never name a script after a standard-library module: scripts run with their own folder first on `sys.path`, so a `select.py` broke the review server.
