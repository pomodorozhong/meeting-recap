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

The audio (10.5 MB) is not committed. [`reference/`](reference/) holds the `segments.json`, `transcript.json` and `manifest.json` of the run with seed 7. It also holds `recap-key.json`, the answer key for scoring a recap of the call (see [Score a run](#score-a-run)). That run reproduces exactly: two runs on an M2 Pro (macOS 26.6.2) gave the same `call_sha256`. On other hardware or MLX builds, compare your manifest's `call_sha256` with the committed one before trusting `reference/`; if they differ, use your own `out/script/` files as the ground truth.

### Intelligibility

Whisper Large v3 (Chinese) heard the seed-7 call with a 5.9% character error rate over 1,377 characters, counting each turn on its own after converting to Simplified and dropping punctuation. Most errors are on short turns and English words: `ryan`'s 「真的嗎」 came out as "Cinema", `dylan`'s 「開 schema」 as 「看SK嘛」, and the overlapping 「對對對」 as a single 「對」. This is a rough check, not a verdict; the user listens before the call is used.

### Voices

Every voice is a preset speaker from the model card; there is no cloning. By ear, four presets speak this mix of Mandarin and English well: `vivian` (female, Mandarin), `dylan` (male, Beijing Mandarin), `ryan` and `aiden` (male, made for English). The script uses `vivian`, `dylan` and `ryan`, with `aiden` spare.

Rejected on 2026-10-29: Qwen3-TTS's other presets; Kokoro-82M's eight Mandarin voices, which garble English terms; CosyVoice-300M-SFT's built-in voices, whose English is imprecise; and CosyVoice 2 and 3 clones.

## Run

```bash
uv run --project experiments/synthetic-call experiments/synthetic-call/generate.py
```

From this folder, `uv run generate.py` is enough.

Further arguments set the script, the output folder and the seed (default 7). The first run downloads the model (about 4 GB). The call takes about four minutes on an M2 Pro.

## Recording collection and unattended benchmark

The original planning call also serves as the three-speaker baseline in a seven-recording benchmark. Three new scripts add distinct subject matter and a fourth preset voice. The paired variants reuse the clean audio so differences within a pair can be traced to the mix.

| Recording ID | Content and condition |
| --- | --- |
| planning | Original three-speaker sprint planning meeting, 73 turns |
| handoff | Two-speaker incident handoff, 12 turns with a rejected proposal, deadlines and an unresolved cause |
| handoff-channel | Same timing and content, B attenuated by 14 dB, seeded white noise at −42 dBFS RMS throughout |
| logistics | Four-speaker event planning meeting, 14 turns without overlap |
| logistics-overlap | Same utterances, seven handoffs advanced to overlap their predecessor by up to one second |
| stocktake | Held-out single-speaker inventory update with a correction, quantities and an 18-second silent break |
| silence | Twelve seconds of digital silence, with empty text and speaker references |

Build the collection from the repository root. The generator reuses matching seed-7 recordings, stages each new recording before publishing it, and verifies regenerated controls byte for byte. Each folder has its own WAV, manifest, transcript and speaker intervals.

```bash
S=experiments/synthetic-call
uv run --locked --project "$S" "$S/collection.py"
```

Build and set up the [pipeline including Who](../pipelines/whisper-sortformer/README.md#setup-once-needs-the-network), and build `diarexp` as in the [runner guide](../../docs/runners.md). The extended comparisons on the clean scripts use the cached LS-EEND and Community-1 weights from that guide's diarizer sweep. The benchmark checks the cache digests. The pipeline setup caches Whisper. Cache Breeze and the 442 MiB quantized Turbo snapshot with the commands below. The benchmark then runs the models serially and preserves logs and prior cases on failure.

```bash
S=experiments/synthetic-call
uv run --locked --project experiments/mlx hf download eoleedi/Breeze-ASR-25-mlx \
  --revision 172151e3fd93ab6dc841d639f23dd48b24bc8301
uv run --locked --project experiments/mlx hf download mlx-community/whisper-large-v3-turbo-q4 \
  --revision 660c343bbf4e52ac257f0b7d952e5388e6f93bef
RESULTS=$(mktemp -d)
"$S/benchmark.sh" "$RESULTS"
```

Each case writes `scores.json` for the base matrix and `extension/scores.json` including Turbo with text errors, one-to-one speaker-time errors, word-label agreement, wall time and peak footprint, along with the raw model outputs. A case requires a fresh output folder. To retry one case, run `benchmark.sh COLLECTION_DIR NEW_RESULTS_ROOT CASE`, then `compare_fast.sh RECORDING_DIR NEW_RESULTS_ROOT/CASE`. If just the extension fails, move its partial folder aside and rerun `compare_fast.sh` on the completed base case. The extension repeats each ASR twice on the handoff and on silence. It also scores turn order for each speech case with the review skill and validates the resulting dataset. The two clean scripts run the normal recap stage and the same summary model on the exact scripted transcript. See the [experiment report](../../docs/experiments/2026-11-01-synthetic-collection.md) for results, limitations and benchmark audio digests.

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

## Score a run

Two scorers compare a run on `call.wav` with the call's ground truth, so any pipeline or experiment can be measured the same way. Run them from the repository root through this folder's uv project. Its environment is the one that generated the call.

### Who spoke when

```bash
uv run --project experiments/synthetic-call experiments/synthetic-call/score_speakers.py \
  --asr asr.json --segments segments.json --turns turns.json --audio experiments/synthetic-call/out/script/call.wav
```

**Inputs:**
- `--asr`: WhisperKit-shaped JSON with word timestamps.
- `--segments`: the run's diarization, in the `segments` format of [docs/runners.md](../../docs/runners.md).
- `--turns` (optional): the attached transcript, `[{"speaker_id", "text"}]` in spoken order.
- `--audio`, or `--audio-sha256` instead: the run's audio. It must be the call `reference/manifest.json` describes, or the scorer refuses.

**What it reports**, over characters and with the best label mapping (two labels may map to one speaker):
- **Diarization agreement:** each Whisper word is labelled at its own time by the run and by the known turns, so ASR timing errors don't count.
- **Transcript agreement**, with `--turns`: the turns are aligned to the script's text after OpenCC `t2s`, with punctuation and spaces dropped, so a word placed in the wrong turn counts as an error.

### Recap

```bash
python3 experiments/synthetic-call/score_recap.py RUN_DIR MATCHES.json
```

[`reference/recap-key.json`](reference/recap-key.json) lists 24 items a correct recap of this call holds:
- 10 decisions;
- 11 action items, with owners and deadlines, or null when the call states none;
- 2 proposals;
- 1 open question.

It also lists 7 questions the call answers, which a recap must not list as open. Each item gives its script turns and the recap sections where it counts. The key's wording is English, but no scorer compares wording: a person matches recap items to key ids by hand. For judging a Chinese recap, [`reference/recap-key.zh-TW.json`](reference/recap-key.zh-TW.json) gives each id's wording in Traditional Chinese, in the call's own terms. `recap-key.json` stays the key, and only it is read.

**Inputs:**
- `RUN_DIR`: holds the recap's `summary.json`, whose `notes` has the sections `topics`, `decisions`, `action_items`, `proposals` and `open_questions`. It also holds the `transcript.md` it was made from, plus an optional `names.json`. `score_recap.py` describes each one.
- `MATCHES.json`: a hand verdict for every recap item (correct, misplaced, wrong or duplicate) and the key items it states.

**What it reports:**
- key items found, and placed in an accepted section;
- whether the cited timestamps cover each item's script turns;
- recap items by verdict;
- action owners right;
- deadlines right.

**Where the key came from:** it was written from the script on 2026-11-01 for the [recap accuracy check](https://github.com/pomodorozhong/meeting-recap/issues/28) and frozen before any recap was scored. Two answered questions (X6, X7) were added after the first recap was read. Its SHA-256 is `4ef8c91b657d56528bf76b74d8301eb4e11f426636322a8867807a473ecac2e1`. Change it only with a note here, because scores made with different keys can't be compared.

### Tests

```bash
uv run --project experiments/synthetic-call python -m unittest discover -s tests/synthetic_call -t tests/synthetic_call
```

## Pins and licenses

| Part | Pin | License |
| --- | --- | --- |
| [mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16), MLX port of [Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) | `52f4770fd9726457eae3d3b6aa92047a25a10776` | Apache-2.0 |

Dependencies are declared in [`pyproject.toml`](pyproject.toml) and every package is pinned in [`uv.lock`](uv.lock); `uv run` uses both when it runs in this folder or with `--project`. The locked environment reproduced the seed-7 `call_sha256`.

## Input profile for comparable real recordings

To rerun an experiment on another real call instead, the recording should match the one the experiments used: an online call with three people, Taiwanese Mandarin with English terms mixed in, all voices mixed into one mono track, 20–65 minutes, converted to 16 kHz mono WAV. Note any difference (more people, people sharing a room, separate tracks) in the experiment's summary, since Sortformer's results are known only for this profile.
