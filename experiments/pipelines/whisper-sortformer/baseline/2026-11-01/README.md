# Synthetic-call baseline, 2026-11-01

Saved outputs of the pipeline on the [synthetic call](../../../../synthetic-call/README.md), once with each diarizer. They back the [baseline section of the pipeline README](../../README.md#baseline-on-the-synthetic-call-2026-11-01). The call is generated, so nothing here is private.

| Folder | Command |
| --- | --- |
| `sortformer/` | `recap.py run experiments/synthetic-call/out/script/call.wav <out>` |
| `who/` | `recap.py run experiments/synthetic-call/out/script/call.wav <out> --diarizer who` |

## How these were made

- **Code:** both runs used commit `07a547ad5cde82c40ef44f1c8b81fb2b0c6ca094`, with a clean pipeline folder (`code_commit` in each `run.json`).
- **Input:** `call.wav` from `experiments/synthetic-call/generate.py` with seed 7. Its SHA-256 `6b7011c6…2a25d48` matches `experiments/synthetic-call/reference/manifest.json`.
- **Machine:** MacBook Pro, Apple M2 Pro, 16 GB, macOS 26.6.2, with nothing else heavy running.
- **Tools:**
  - Swift 6.3.3 from the Command Line Tools;
  - ffmpeg 9.0.2;
  - Python 3.12.13 through uv, with the packages in `../../uv.lock`;
  - Swift packages as in `../../Package.resolved`.
- **Models:** the pinned revisions in `run.json`.
  - The cached Sortformer weights matched the SHA-256s in `docs/runners.md`.
  - Who's int8 weights came from the SDK's `v0.3.4`, which resolved to `desert-ant-labs/who` commit `f026f4604f874e2cfe6b817e5123c2b64a56683d`.

## What is kept, and what changed

Each folder holds every file the run wrote except the following:
- **Left out:**
  - `audio.wav` (10.5 MB): regenerate it from the call.
  - `logs/*.log`: they hold local paths.
  - Hidden partial files.
- **Kept:** the `logs/*.time` files, which are the `/usr/bin/time -l` reports behind `stages.json`.
- **Changed:** `sortformer/sortformer.raw.json`'s `audioFile` field held the run's local path to `audio.wav`. It now says `audio.wav`, so that file no longer matches its digest in `stages.json`. Nothing else was edited.

`sortformer/` is the run as it came out, with Sortformer's spare fourth label still named `Speaker D` in `speakers.json`. The recap accuracy check merged that label into Speaker C before it re-summarized.

## Score them

From the repository root:

```bash
uv run --project experiments/pipelines/whisper-sortformer experiments/pipelines/whisper-sortformer/score_speakers.py experiments/pipelines/whisper-sortformer/baseline/2026-11-01/sortformer
```

| Run | Labels | Turns (script 73) | Diarization agreement | Transcript agreement |
| --- | --- | --- | --- | --- |
| `sortformer` | 4 (two map to Speaker C) | 67 | 98.2% of 1,412 characters | 95.1% of 1,317 aligned |
| `who` | 3 | 65 | 98.5% of 1,412 characters | 95.8% of 1,317 aligned |

`score_speakers.py` explains both measures. It refuses a run whose input doesn't match the reference's `call_sha256`.

## Repeatability

These are second runs. The first ones, which the pipeline README's tables first reported, were made earlier the same day on the same machine with the same code.

| Output | Same as the first run? |
| --- | --- |
| Whisper segments and words | Identical in both runs (only `elapsed_seconds` differs) |
| Sortformer segments and attached turns | Identical |
| Who recap | Identical reply |
| Sortformer recap | Same section counts as first reported (6 topics, 7 decisions, 10 action items, 3 proposals, 2 open questions). The first run's file wasn't kept, so it can't be compared word for word |

ASR, Sortformer and the recaps came within 1–6% of the first runs. Who's step took 1.1 s against 2.1 s. Its own load and diarize times were 0.3 s and 0.7 s both times, so the difference is process start-up:

| Run | ASR | Diarize | Recap | Total |
| --- | --- | --- | --- | --- |
| `sortformer` | 49 s | 138 s | 104 s | 292 s |
| `who` | 49 s | 1.1 s | 87 s | 137 s |

MLX peaks were the same (3.96–4.06 GB for ASR, 6.71 GB for the recap).

On another Mac, or with other macOS, MLX or Core ML builds, expect the same pipeline to give close but not identical outputs. Compare your scores with the table above, not file by file.
