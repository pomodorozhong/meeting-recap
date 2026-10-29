---
name: meeting-experiment-review
description: Run local speech experiments (transcription, speaker diarization, label attachment) on private meeting recordings, collect the user's listening judgments in a local review page, and score runs against confirmed references. Use when comparing ASR or diarization models or settings on a real recording, preparing clips for the user to listen to, recording what the user heard, or evaluating speaker separation without a hand-made reference transcript.
---

# Meeting Experiment Review

Recordings, transcripts, and the user's answers are private. Every artifact lives in a **private dataset directory outside any Git checkout**; the scripts refuse to create one inside a repository. Never copy audio, transcript text, speaker names, or answers into a repo, issue, PR, commit, or chat summary beyond what the user asks for.

All helpers are standard-library Python 3.11+ in `scripts/`. Run them as `python3 <skill>/scripts/<name>.py`. Every command prints JSON; failures exit nonzero with a one-line reason.

## Ground rules

- **Artifacts are immutable.** Recordings, runs, sessions, references, and evaluations are written once with SHA-256 digests. To change a prediction, register a new run ID; never edit files inside the dataset by hand. `dataset.py validate` detects changes.
- **Only the user confirms ground truth.** Answers come from the review page or from a JSON file holding exactly what the user said. Never fill in a `confirmed` answer from a model output, a participant list, or your own guess. If the user is unsure, record `unsure`.
- **Keep claims inside the evidence.** The evaluation measures speaker turn order on selected clips. It is not DER, not transcript accuracy, and not an error rate for the whole recording. Say so when reporting.
- **Compare like with like.** One evaluation covers runs on the same recording and the same reference clips; the script rejects anything else.

## Workflow

### 1. Create the dataset and add recordings

```bash
python3 scripts/dataset.py init ~/meeting-review-data
ffprobe -v error -show_entries format=duration -of csv=p=0 call-part1.mp4
python3 scripts/dataset.py add-recording ~/meeting-review-data --id part1 --audio call-part1.mp4 --duration 1343.2 --group call-2026-10-22
```

Parts of one call share a `--group`. The media is copied into the dataset. Models usually want 16 kHz mono WAV; convert with `ffmpeg -i in.mp4 -ac 1 -ar 16000 -c:a pcm_f32le out.wav` and register the WAV if runs use its time origin.

### 2. Produce and register runs

Runs can come from any tool that writes the formats in [references/formats.md](references/formats.md); this repository's runners are described in `docs/runners.md`. Write raw output to a scratch directory, then register each output with a run spec:

```json
{"id": "sortformer-part1", "recording_id": "part1", "model": "fluidaudio-sortformer",
 "status": "completed", "artifacts": {"segments": "sortformer_seg.json"},
 "config": {}, "runtime": {"wall_seconds": 1560, "peak_rss_mb": 1500}, "notes": ""}
```

```bash
python3 scripts/dataset.py add-run ~/meeting-review-data --spec run.json
```

Artifact paths are relative to the spec file. Use `segments` for diarization output and `transcript` for WhisperKit-shaped ASR JSON; formats are in [references/formats.md](references/formats.md). Record failed or partial runs too, with `status` `failed` or `incomplete`.

To label transcript text with diarization speakers, derive a new run:

```bash
python3 scripts/attach.py ~/meeting-review-data --asr-run whisper-part1 --diarization-run sortformer-part1 --id attached-part1 --method word
```

`word` (default) needs word timestamps; `seg` attaches whole ASR segments by overlap; `line` reproduces HushScribe's single-point lookup for comparison.

### 3. Choose clips and prepare a session

Pick clips that answer the user's question: speaker changes, overlaps, short interjections, places where runs disagree, unclear words, and names or technical terms. Give each clip a reason. Keep clips short (5–30 s) and the session small enough to finish in one sitting (about 10–20 items).

```json
{"id": "turns-part1", "question": "Which diarizer keeps three speakers apart?",
 "selector": {"name": "agent-selected", "version": "1"},
 "items": [{"id": "c01", "task": "speaker_order", "recording_id": "part1",
            "start_seconds": 312.0, "end_seconds": 327.5, "padding_seconds": 1,
            "reason": "Runs disagree on a quick hand-off", "run_ids": ["sortformer-part1", "community1-part1"]}]}
```

`task` is `speaker_order` (who speaks, in order) or `transcript` (what was said). `run_ids` choose which predictions the page can show next to the clip.

```bash
python3 scripts/review.py prepare ~/meeting-review-data --plan plan.json
```

### 4. Collect the user's answers

```bash
python3 scripts/review.py serve ~/meeting-review-data --session turns-part1
```

Run it in the background and give the user the printed `http://127.0.0.1:…/?token=…` URL; do not log or repeat the token elsewhere. The page plays each clip, shows predictions, and saves answers, notes, and optional voice feedback to the dataset. Speaker IDs in answers are the user's own stable names or initials for each person, used consistently across the session. Stop the server when the user is done.

If the user answers in chat instead, write their exact answer to a JSON file outside the repo and save it:

```json
{"item_id": "c01", "state": "confirmed", "annotation": {"speaker_order": ["A", "B", "A"]}, "feedback_text": ""}
```

```bash
python3 scripts/review.py answer ~/meeting-review-data --session turns-part1 --file answer.json
```

States are `confirmed`, `unsure`, `skipped`, `unusable`. A confirmed `speaker_order` needs an explicit list (empty for no speech); set `"allow_extra_turns": true` when the user says brief extra turns are acceptable. A confirmed `transcript` needs `text`.

### 5. Freeze a reference and evaluate

```bash
python3 scripts/review.py close ~/meeting-review-data --session turns-part1
python3 scripts/review.py reference ~/meeting-review-data --session turns-part1 --id ref-part1
python3 scripts/evaluate.py ~/meeting-review-data --reference ref-part1 --runs sortformer-part1 community1-part1 --id eval-part1
```

The reference keeps only confirmed items and lists the rest as excluded. The evaluation writes `evaluations/<id>/evaluation.json` and `report.md` with turns recovered and clips correct per run. By default each run's labels are mapped to people in whichever way scores best, which flatters runs; pass `--mappings mappings.json` (`{"run-id": {"label": "A"}}`) to test a fixed naming. Only completed runs can be scored.

### 6. Report

Lead with the decision the user asked about. Give the table, the number of excluded items, the mapping method, and the limit stated in the report. Separate what was measured from what was only listened to. Note anything unresolved as an open question rather than a conclusion.

## Other checks

`python3 scripts/dataset.py validate <dataset>` rechecks every digest and the event logs.
