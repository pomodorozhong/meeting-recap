# Synthetic call

A short, shareable three-person call for running the runners, the pipeline, and the review skill without private data ([#4](https://github.com/pomodorozhong/meeting-recap/issues/4)). Status: generated, and scored end to end with Sortformer and the review skill.

## What it makes

[`script.json`](script.json) is a fictional sprint-planning call in Taiwanese Mandarin with English product terms: three speakers (A, B, C), 73 turns over 5.5 minutes, with short interjections, an interruption, and four overlaps (a negative `gap_seconds`). It covers a login bug, dashboard performance, a push-notification feature, CI and Docker tech debt, and a demo date.

[`generate.py`](generate.py) speaks a script with Qwen3-TTS CustomVoice's preset speakers through MLX on the GPU, and writes, under `out/<script name>/` (ignored by Git):

| File | Holds |
| --- | --- |
| `call.wav` | The call, 16 kHz mono PCM, each turn levelled to the same loudness |
| `turns/NN-<speaker>.wav` | Each turn on its own |
| `segments.json` | Ground-truth speaker turns in the `segments` format, labels `A`/`B`/`C` |
| `transcript.json` | Ground-truth text per turn in the `transcript` shape (no word times) |
| `manifest.json` | Model revision, seed, voices, duration, run time, and the call's sha256 |

The audio (10.5 MB) is not committed. [`reference/`](reference/) holds the `segments.json`, `transcript.json` and `manifest.json` of the run with seed 7. That run reproduces exactly: two runs on an M2 Pro (macOS 26.6.2) gave the same `call_sha256`. On other hardware or MLX builds, compare your manifest's `call_sha256` with the committed one before trusting `reference/`; if they differ, use your own `out/script/` files as the ground truth.

### Intelligibility

Whisper Large v3 (Chinese) heard the seed-7 call with a 5.9% character error rate over 1,377 characters, counting each turn on its own after converting to Simplified and dropping punctuation. Most errors are on short turns and English words: `ryan`'s 「真的嗎」 came out as "Cinema", `dylan`'s 「開 schema」 as 「看SK嘛」, and the overlapping 「對對對」 as a single 「對」. This is a rough check, not a verdict; the user listens before the call is used.

### Voices

Every voice is a preset speaker from the model card; there is no cloning. By ear, four presets speak this mix of Mandarin and English well: `vivian` (female, Mandarin), `dylan` (male, Beijing Mandarin), `ryan` and `aiden` (male, made for English). The script uses `vivian`, `dylan` and `ryan`, with `aiden` spare.

Rejected on 2026-10-29: Qwen3-TTS's other presets; Kokoro-82M's eight Mandarin voices, which garble English terms; CosyVoice-300M-SFT's built-in voices, whose English is imprecise; and CosyVoice 2 and 3 clones.

## Run

```bash
uv run experiments/synthetic-call/generate.py
```

Further arguments set the script, the output folder and the seed (default 7). The first run downloads the model (about 4 GB). The call takes about four minutes on an M2 Pro.

## Use with the review skill

Keep the dataset outside the checkout (the skill refuses one inside it). From the repository root, with `DATASET` set to a new folder:

```bash
SKILL=.agents/skills/meeting-experiment-review/scripts
python3 $SKILL/dataset.py init "$DATASET"
python3 $SKILL/dataset.py add-recording "$DATASET" --id synthetic --audio experiments/synthetic-call/out/script/call.wav --duration 329.88
python3 $SKILL/review.py known "$DATASET" --recording synthetic --segments experiments/synthetic-call/reference/segments.json --id truth
```

Then run a diarization runner from [docs/runners.md](../../docs/runners.md) on `call.wav`, register its `segments` with `dataset.py add-run`, and score it with `evaluate.py --reference truth`. `review.py known` cuts the call into 10 clips of about 30 seconds with 72 reference turns.

Smoke test, 2026-10-29: Sortformer (FluidAudio, as pinned in docs/runners.md) recovered 67 of 72 turns and got 7 of 10 clips fully right, with the best-fitting label mapping. The misses were in clips 1, 7 and 10: two short B turns and an A turn went unnoticed, and near the end one C turn went to a fourth label that Sortformer used for only 0.6 s.

## Pins and licenses

| Part | Pin | License |
| --- | --- | --- |
| [mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16), MLX port of [Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) | `52f4770fd9726457eae3d3b6aa92047a25a10776` | Apache-2.0 |

Python dependencies are pinned in the script header.

## Input profile for comparable real recordings

To rerun an experiment on another real call instead, the recording should match the one the experiments used: an online call with three people, Taiwanese Mandarin with English terms mixed in, all voices mixed into one mono track, 20–65 minutes, converted to 16 kHz mono WAV. Note any difference (more people, people sharing a room, separate tracks) in the experiment's summary, since Sortformer's results are known only for this profile.
