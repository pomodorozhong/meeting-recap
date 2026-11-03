# Synthetic call

A short, shareable three-person call for running the runners, the pipeline, and the review skill without private data ([#4](https://github.com/pomodorozhong/meeting-recap/issues/4)). The collection uses pinned F5-TTS and EmotiVoice female profiles with Qwen3-TTS male presets. See the [seventeen-recording collection](#seventeen-recording-collection) for other speaker counts and controlled changes to the audio.

## What it makes

[`script.json`](script.json) is a fictional sprint-planning call in Taiwanese Mandarin with English product terms: three speakers (A, B, C), 73 turns, with short interjections, an interruption, and four overlaps (a negative `gap_seconds`). It covers a login bug, dashboard performance, a push-notification feature, CI and Docker tech debt, and a demo date.

[`generate.py`](generate.py) speaks Qwen and F5 turns through MLX on the GPU and batches EmotiVoice turns in the locked CPU project. It writes under `out/<script name>/` (ignored by Git).

| File | Holds |
| --- | --- |
| `call.wav` | The call, 16 kHz mono PCM, each turn levelled to the same loudness |
| `turns/NN-<speaker>.wav` | Each turn on its own |
| `segments.json` | Ground-truth speaker turns in the `segments` format, labels `A`/`B`/`C` |
| `transcript.json` | Ground-truth text per turn in the `transcript` shape (no word times) |
| `manifest.json` | Model revision, seed, voices, duration, run time, and the call's sha256 |

Audio is generated locally. [`reference/`](reference/) holds the planning call's `segments.json`, `transcript.json` and `manifest.json`. It also holds the recap answer key (see [Score a run](#score-a-run)). Turn text and speaker IDs stay fixed when the voice changes, while the timed references and WAV hashes are regenerated together. Compare your WAV SHA-256 with the committed manifest before using these reference times. Other hardware or MLX builds can produce different bytes.

### Voices and the English-word gate

The F5 female profile is `f5-news-female`, generated with F5-TTS v1 4-bit through `f5-tts-mlx`. It uses the published `news-female.wav` demo reference from a pinned ZipVoice release. [`reference/f5-voice.json`](reference/f5-voice.json) records the archive URL and SHA-256, exact member, reference WAV hash and transcript, model and vocoder revisions, per-file hashes, and sampling settings. The reference clip is downloaded to the Hugging Face cache and checked before inference. Its source archive does not state a separate license for that reference recording.

Every F5 turn specifies `tts_duration_seconds` in its script. The handoff call's three voice-check turns use 4.5, 5.5 and 3.8 seconds with seed 7, eight RK4 steps and CFG 2. The automatic duration predictor produced unusable output in this setup. The male voices are the pinned Qwen presets `dylan`, `ryan` and `aiden`.

The localization call has three female speakers with EmotiVoice presets `emotivoice-1093`, `emotivoice-1012` and `emotivoice-1066`. Each ID selects its own factory speaker embedding. [The EmotiVoice pins](emotivoice/pins.json) cover source code, model and SimBERT files, phoneme resources and synthesis settings. Its [locked CPU project](emotivoice/pyproject.toml) uses Torch 2.10.0 and Transformers 4.57.6, matching the runtime these presets were auditioned with. Those auditions are kept outside this repository. The main generator runs this child project once for all EmotiVoice turns before loading GPU models. The manifest records the selected voice pins and the child runtime lock hash.

| Call speaker | Female profile |
| --- | --- |
| Planning A, handoff B, logistics A, scheduling A, design B, onboarding A | F5 female news voice |
| Localization A | EmotiVoice 1093 |
| Localization B | EmotiVoice 1012 |
| Localization C | EmotiVoice 1066 |

The three EmotiVoice profiles also pass the same English-word gate after level adjustment. Their native renders match the reference renders from the voice selection byte for byte. That selection audio is kept outside this repository.


The F5 voice passed a fixed three-turn Mandarin screen. Unprompted Whisper Large v3 at revision `49e6aa286ad60c14352c404340ded53710378a11`, forced to Chinese with temperature zero and previous-text conditioning disabled, must recover standalone `log` and `timeout` in their original turns. A second decode checks word timestamps against turn boundaries with a 0.2-second tolerance. Mandarin character agreement after OpenCC conversion must reach 65%. The selected voice reached 97.9%, and independent process launches produced identical WAV bytes. After building the collection below, run the same gate on its generated, levelled 16 kHz handoff turns. It writes a JSON report with input hashes, recognition text, turn checks and the verdict.

```bash
uv run --locked --project experiments/synthetic-call python \
  experiments/synthetic-call/check_voice.py "$OUT/handoff"
```

This screen covers intelligibility on the fixed script. Listening review determines naturalness and consistency.

### Historical checks

The earlier all-Qwen planning call had SHA-256 `6b7011c6057821e04fe1b3cd78659297218e83d0ed899496e769eb4992a25d48`. Its measured Whisper character error rate was 5.9%, and the earlier Sortformer review recovered 67 of 72 reference turns with seven of ten clips fully correct. Those results describe the earlier audio. Its source and reference files are preserved at commit `e208026`, which is in #32's PR history but not on `main`.

## Run

```bash
uv run --project experiments/synthetic-call experiments/synthetic-call/generate.py
```

From this folder, `uv run generate.py` is enough.

Further arguments set the script, the output folder and the seed (default 7). The first run downloads the pinned speech models, vocoder and reference archive.

## Seventeen-recording collection

[collection.py](collection.py) builds fourteen fictional calls with the existing generator and seed 7, then derives three controls. The collection has seventeen main `call.wav` recordings, including fourteen scripted calls. Each folder contains `call.wav` (16 kHz mono PCM16), `transcript.json` (scripted text and turn times), `segments.json` (speaker intervals), and a manifest. The transcript is the intended script, not a listening judgment.

| Folder | Input |
| --- | --- |
| `script` | The existing three-speaker planning call, 73 turns |
| `handoff` | Two-speaker incident handoff, 12 turns |
| `logistics` | Four-speaker event planning call, 14 turns |
| `stocktake` | Single-speaker inventory update, six turns with an 18-second pause |
| `scheduling` | Two speakers, 12 turns. The final appointment is Friday at 10:00 with seven seats and copies, after explicit corrections |
| `design` | Three speakers, 15 turns. A five-minute cache replaces daily updates, backend ownership moves from B to C, and retention stays unresolved |
| `onboarding` | Four speakers, 16 turns. C and D join late, speak twice each, and A returns after a 12-second pause |
| `localization` | Three female speakers, 15 turns. Corrected error wording, rejected troubleshooting advice and an unresolved export check |
| `english-audit` | One speaker, 15 turns. Equipment counts, corrected quantities and measurements, a silent break, and an unresolved repair |
| `english-handoff` | Two speakers, 20 turns. Incident thresholds, rejected remedies, deadlines and a provisional test |
| `english-design` | Three speakers, 20 turns. Reversed export decision, reassignment, corrected deadlines and deferred retention |
| `english-tabletop` | Four speakers, 24 turns. Late arrival, corrected seat counts, delivery costs and accessibility measurements |
| `english-committee` | Three female speakers, 21 turns. Maintenance costs, booking hours, rejected work and pending fees |
| `english-training` | Two speakers, 22 turns. Checkbacks, corrected scan settings, spelled acronyms and return after silence |
| `handoff-channel` | Handoff with speaker B attenuated by 14 dB and seeded noise at −42 dBFS RMS; the reference timing stays fixed |
| `logistics-overlap` | The same logistics utterances with seven overlapping handoffs; both reference files move with the audio |
| `silence` | Twelve seconds of digital silence with empty text and speaker intervals |

A whole-call sanity decode of `onboarding` with the pinned Whisper Large v3 checkpoint, greedy Chinese decoding and previous-text conditioning disabled inserted unrelated text around the 12-second pause and omitted some following turns. The fixture preserves the scripted speech and exact pause for evaluating this failure. The intended transcript and speaker intervals come from generation.

From the repository root:

```bash
S=experiments/synthetic-call
OUT=$(mktemp -d)
uv run --locked --project "$S" python "$S/collection.py" "$OUT"
uv run --locked --project "$S" python "$S/collection.py" "$OUT" --check
```

The first command builds missing recordings in staging directories and reuses matching completed ones. Both commands verify the WAV, transcript and speaker intervals against [the collection hashes](reference/collection-sha256.json). They also verify the fourteen source scripts and each manifest's provenance; elapsed synthesis time can vary. An existing file that differs is left intact and reported by name. Use a fresh output directory to rebuild it. `--check` reads existing files without loading TTS or generating audio.

The hashes describe seed 7 on the reference M2 Pro with the committed model revisions, female-reference hash, explicit F5 turn durations and uv lock. Other hardware or MLX versions can produce different bytes. To generate a local variant with its own references, run `generate.py` directly as described above.

## English coverage and transcript regression checks

The six English scripts contain **2,947 scripted words** and produce **19.04 minutes** of audio on the reference machine. They span one through four speakers and use five voice profiles. Each sets `"language": "en"`. The generator selects English for Qwen and records that language in the manifest. The other scripts use the Mandarin default.

The coverage tests require at least six English scripts, 2,400 words, five voices and one/two/three/four-speaker cases. Every English-tagged turn must contain English speech without CJK characters.

| English voice | Calls |
| --- | --- |
| EmotiVoice 1093 | Audit A, design B, committee A |
| EmotiVoice 1012 | Handoff A, tabletop A, committee B |
| EmotiVoice 1066 | Design A, tabletop B, committee C, training A |
| Qwen Aiden | Handoff B, tabletop C |
| Qwen Ryan | Design C, tabletop D, training B |

[`score_transcripts.py`](score_transcripts.py) reads `RUNS/<call>/asr.json` for **every scripted call**. Each JSON contains either a top-level `text` string or `segments` with `text` strings. An optional `audio_sha256` must match the reference WAV. The tool also records each ASR file's hash.

English uses word error rate (WER), normalized with the pinned Transformers Whisper English normalizer for numbers and contractions. Mandarin uses character error rate (CER), after OpenCC conversion and removal of punctuation and spaces. Source calls are scored once each. The matched controls are evaluated separately with the existing tools.

[`transcribe_collection.py`](transcribe_collection.py) recreates the Whisper component baseline with model revision `49e6aa286ad60c14352c404340ded53710378a11`, forced language per script, temperature zero and previous-text conditioning disabled. It verifies the complete collection before loading Whisper, reuses reports with matching audio/script/model/settings provenance and refuses stale reports. Archive a stale report before intentionally decoding changed inputs again.

```bash
RUNS=$(mktemp -d)
uv run --locked --project "$S" python "$S/transcribe_collection.py" "$OUT" "$RUNS"
uv run --locked --project "$S" python "$S/score_transcripts.py" "$OUT" "$RUNS" \
  --output current-scores.json --baseline "$S/reference/transcript-baseline.json"
uv run --locked --project "$S" python "$S/score_transcripts.py" "$OUT" CANDIDATE_RUNS \
  --output candidate-scores.json --baseline "$S/reference/transcript-baseline.json"
```

The committed [component baseline](reference/transcript-baseline.json) records **1.88% English WER** (57 errors / 3,028 normalized words, six calls) and **9.27% Mandarin CER** (287 / 3,095 characters, eight calls), with per-call scores, exact input hashes, normalizer versions and recognizer settings. Normalized word counts differ from source word counts because contractions and numbers are expanded. These are recognizer component results; for the full pipeline on this collection, see [its comparison](../../docs/experiments/2026-11-02-synthetic-collection-pipeline.md). The English training checkback was rewritten after the first screen found garbled speech, then regenerated and checked again. Its final whole-call WER is 2.09%.

The report has separate English and Mandarin groups. Comparison exits with an error if either group's error rate increases, so improvement in Mandarin cannot conceal an English regression. Missing run files, mismatched reference hashes or changed normalization also fail. `--maximum-regression` sets an allowed absolute rate increase per language, with zero as the default. Reports use distinct output paths to protect the baseline and source data.

## Use with the review skill

Keep the dataset outside the checkout (the skill refuses one inside it). From the repository root, with `DATASET` set to a new folder:

```bash
SKILL=.agents/skills/meeting-experiment-review/scripts
python3 $SKILL/dataset.py init "$DATASET"
DURATION=$(python3 -c 'import json; print(json.load(open("experiments/synthetic-call/out/script/manifest.json"))["duration_seconds"])')
python3 $SKILL/dataset.py add-recording "$DATASET" --id synthetic --audio experiments/synthetic-call/out/script/call.wav --duration "$DURATION"
python3 $SKILL/review.py known "$DATASET" --recording synthetic --segments experiments/synthetic-call/reference/segments.json --id truth
```

Then run a diarization runner from [docs/runners.md](../../docs/runners.md) on `call.wav`, register its `segments` with `dataset.py add-run`, and score it with `evaluate.py --reference truth`. `review.py known` cuts the generated call into review clips using the current speaker intervals.

## Score a run

Two scorers compare a run on `call.wav` with the call's ground truth, so any pipeline or experiment can be measured the same way. Run them from the repository root through this folder's uv project. Its locked environment generates the current call. Earlier model scores use the earlier reference snapshot and audio hash.

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

## Model count and disk space

Generating the complete collection uses **three TTS systems**: Qwen3-TTS, F5-TTS and EmotiVoice. Including the separately downloaded Vocos and SimBERT supporting models, this is **five model packages using about 6.58 GB on disk**. The seven voice profiles share these weights; selecting another preset does not require another model download.

The following sizes were measured from the pinned cached files on the reference Mac on **2026-11-02**. They count allocated disk space with cache symlinks resolved and each underlying file counted once. Units are decimal: 1 GB = 1,000,000,000 bytes and 1 MB = 1,000,000 bytes. Filesystem allocation and rounding can change the reported sizes slightly.

| Model package | Role | Disk space |
| --- | --- | ---: |
| Qwen3-TTS 1.7B BF16, including its speech tokenizer | Aiden, Ryan and Dylan voice presets | 4.52 GB |
| F5-TTS v1, 4-bit | Female news voice | 232 MB |
| Vocos | F5 vocoder | 54 MB |
| EmotiVoice checkpoints | Female presets 1093, 1012 and 1066 | 1.39 GB |
| SimBERT | EmotiVoice text/style encoder | 386 MB |
| **Generation total** | **Five model packages** | **6.58 GB** |
| Whisper Large v3 MLX | Voice checks and transcript baseline | 3.08 GB |
| **Generation and verification total** | **Six model packages** | **9.66 GB** |

The pinned reference WAV, EmotiVoice source and NLTK frontend resources add roughly **29 MB**. These figures exclude Python environments, generated audio, other cached revisions and models tried during voice selection. The revisions and file hashes for the generation models are recorded below, in [`reference/f5-voice.json`](reference/f5-voice.json) and [`emotivoice/pins.json`](emotivoice/pins.json). The verification model is pinned in [`transcribe_collection.py`](transcribe_collection.py) and [`check_voice.py`](check_voice.py).

## Pins and licenses

| Part | Pin | License |
| --- | --- | --- |
| [mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16), MLX port of [Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) | `52f4770fd9726457eae3d3b6aa92047a25a10776` | Apache-2.0 |
| [F5-TTS MLX v1 4-bit](https://huggingface.co/lucasnewman/f5-tts-mlx), converted from [SWivid/F5-TTS](https://huggingface.co/SWivid/F5-TTS) | `2d719cadec8fd3887c8599475a5f65924d523654`, used files SHA-256 pinned | Original pretrained weights CC-BY-NC-4.0, MLX runtime code MIT |
| [Vocos MLX](https://huggingface.co/lucasnewman/vocos-mel-24khz) | `ee89d00fac94b61e1235e0869f3e8d49711b7484`, used files SHA-256 pinned | MIT |
| [EmotiVoice](https://github.com/netease-youdao/EmotiVoice) source and [published weights](https://huggingface.co/FPVG/EmotiVoice-pretrained-models) | Source `59f0f36de4db12825f4705dd4e0780d79dd6bb01`, weights `25c5d915525d8f661ad10a13c2b8e958b45a3d8a`, source and artifact SHA-256 pinned | Apache-2.0 upstream |
| [SimBERT encoder mirror](https://huggingface.co/WangZeJun/simbert-base-chinese) | `8096d1f9a7f7c2d9dbd7974511c4bc4a1755932b`, all used files SHA-256 pinned | Apache-2.0 upstream SimBERT and bert4vec |
| NLTK phoneme frontend resources | Immutable NLTK data revision and ZIP/extracted-file SHA-256 in `emotivoice/pins.json` | Resource metadata retained in pinned archives |
| Published female reference in [ZipVoice demo archive](https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/sherpa-onnx-zipvoice-distill-int8-zh-en-emilia.tar.bz2) | Archive and exact reference WAV SHA-256 in `f5-voice.json` | Reference-specific redistribution terms are unstated in that archive |

Dependencies are declared in [`pyproject.toml`](pyproject.toml) and every package is pinned in [`uv.lock`](uv.lock); `uv run` uses both when it runs in this folder or with `--project`. The root environment and isolated EmotiVoice environment each have a committed lock. Check both with `uv lock --check --project experiments/synthetic-call` and `uv lock --check --project experiments/synthetic-call/emotivoice`. The generator prepares the locked child environment automatically when an EmotiVoice speaker is present.

## Compare the pipeline on this collection

[`collection_run.sh`](collection_run.sh) runs [the 17-recording comparison](../../docs/experiments/2026-11-02-synthetic-collection-pipeline.md) up to its hand grading, and [`collection_setup.sh`](collection_setup.sh) prepares what it needs. The summary's Reproduce section gives the commands. These runners live here, not in their own experiment folder, because they import `collection.py` and nothing imports across experiment folders; they reach the pipeline and MLX runners only through their commands.

## Input profile for comparable real recordings

To rerun an experiment on another real call instead, the recording should match the one the experiments used: an online call with three people, Taiwanese Mandarin with English terms mixed in, all voices mixed into one mono track, 20–65 minutes, converted to 16 kHz mono WAV. Note any difference (more people, people sharing a room, separate tracks) in the experiment's summary, since Sortformer's results are known only for this profile.
