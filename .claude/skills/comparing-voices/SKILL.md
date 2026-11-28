---
name: comparing-voices
description: Build and open a local web page that plays the synthetic collection's calls in two or more voice versions side by side, turn by turn, with a blind mode and notes, so the project owner can listen and judge them. Use when the user asks to compare, listen to, or audition voices or TTS output, and offer it right after a new TTS generator (such as generate_<tts>.py) has voiced the collection scripts, since a listen is part of judging a new voice. Not for scoring transcripts or for real recordings.
---

# Comparing voices

[`compare_voices.py`](../../../experiments/synthetic-call/compare_voices.py) builds the page; this skill says which folders to give it, how to open it, and what to do with the notes. Everything on the page is synthetic audio, so it holds nothing private, but it reads the collection from the private review dataset: never commit the built page or its links.

## 1. Pick the versions

Each version is a folder of generated calls in the collection's layout (`<call>/call.wav`, `turns/`, `transcript.json`, `manifest.json`).

- **Current collection, always first.** The newest `seventeen-fixtures-*` folder (or a later collection) under `$MEETING_REVIEW_DATA/benchmarks/synthetic-recording-collection/`. If there is more than one candidate, or none, ask the user.
- **The new voice:** the output folder of its generator, usually `experiments/synthetic-call/out/<tts>/` in the checkout or worktree where it ran. Use the variant the experiment summary reports (for Audio8, the `--simplified` run).
- **Earlier rejected voices** only when the user asks, or when the summary compares against one, such as `out/lfm3/`.

Labels are short lowercase words: `current`, `audio8`, `lfm3`.

## 2. Build

```bash
S=experiments/synthetic-call
uv run --locked --project "$S" python "$S/compare_voices.py" "$S/out/compare" current="$COLLECTION" audio8="$S/out/audio8"
```

It replaces any earlier page in `out/compare/` (Git ignores `out/`) and prints the calls that a version is missing. A missing call or turn shows as unavailable, not an error.

## 3. Open it

In the Claude desktop app, add an entry to the session's `.claude/launch.json` (the folder the session started in, which may not be this repository) and start it with `preview_start`:

```json
{"name": "voice-compare", "runtimeExecutable": "python3",
 "runtimeArgs": ["-m", "http.server", "5207", "--bind", "127.0.0.1", "--directory", "<absolute path to out/compare>"],
 "port": 5207}
```

Elsewhere, give the user the same `python3 -m http.server …` command and `http://127.0.0.1:5207`. Before handing it over, check in the page that `call.wav` and one turn load for every version (a HEAD request on each returns 200).

Tell the user, in a few lines: the left list switches calls (← / → too); each turn has one button per version; on `handoff` the gate's turns are highlighted; blind mode hides and shuffles the versions per call; notes save in the browser and "Copy all notes" copies them to paste back.

## 4. Use the notes

When the user pastes notes, put the verdict in the experiment summary's listening line in their words, marked as an informal listen unless a structured review was run, and with the `experiment-writing` skill. A preference heard only in blind mode is stronger evidence; say which mode it was. Don't turn notes into a score.

## 5. Clean up

When the user is done, stop the server (`preview_stop`) and remove the `launch.json` entry you added. Leave `out/compare/` for the next build to replace.
