# Experiment runners

The scripts in [`experiments/`](../experiments) produce model outputs for the `meeting-experiment-review` skill. Each writes to a scratch `OUT` directory or output path outside the repository. Register the outputs with `dataset.py add-run` afterwards, using the formats in [the skill's formats reference](../.agents/skills/meeting-experiment-review/references/formats.md).

All runs so far used macOS 26.6.2, Apple M2 Pro, 16 GB, Swift 6.3.3.

| Component | Pinned version |
| --- | --- |
| WhisperKit / `whisperkit-cli` | 0.18.0, `e2adabbe7d98dc4d0ab9a5b75424ecc42a9cdbef` |
| FluidAudio / `fluidaudiocli` | `ea500621819cadc46d6212af44624f2b45ab3240` |
| WhisperKit Whisper model | `argmaxinc/whisperkit-coreml/openai_whisper-large-v3` |
| Sortformer model (downloaded by FluidAudio) | `Sortformer_v2.1.mlmodelc`; SHA-256 of `model0/weights/0-weight.bin` `88a98803e35186b1dfb41d7f748f7cee5093bb6efeb117f56953c17549792fa4`, `model1/weights/1-weight.bin` `4c85926af77684bce762b355a2b162df557d832444fbeb79ee195113a4bbf1db` |
| `mlx-whisper` | 0.4.2 |
| MLX Whisper model | `mlx-community/whisper-large-v3-mlx` at `49e6aa286ad60c14352c404340ded53710378a11` |
| MLX Breeze model | `eoleedi/Breeze-ASR-25-mlx` at `172151e3fd93ab6dc841d639f23dd48b24bc8301` |
| Breeze-ASR-25 (transformers) | `MediaTek-Research/Breeze-ASR-25` at `cffe7ccb404d025296a00758d0a33468bec3a9d0` |

Input audio for all runners is 16 kHz mono WAV:

```bash
ffmpeg -i recording.mp4 -ac 1 -ar 16000 -c:a pcm_f32le recording-16k.wav
```

The conversion keeps the source's time origin, so outputs line up with the original media registered in the dataset.

## `experiments/diarization/`

Swift package `diarexp` for FluidAudio's offline (Community-1) diarizer, plus `fluidaudiocli` for Sortformer and LS-EEND.

```bash
cd experiments/diarization
swift build -c release && swift build -c release --product fluidaudiocli
AUDIO=recording-16k.wav OUT=/scratch/dia ./run_sweep.sh
```

- Building `fluidaudiocli` takes about two minutes. FluidAudio downloads its models on first use to `~/Library/Application Support/FluidAudio/Models`.
- `diarexp <wav> <out.json> [key=value ...]` writes `segments` JSON directly. Keys: `num`, `min`, `max`, `thr`, `minseg`, `excl`, `exovl`, `step`, `mingap`, `fa`, `fb`.
- The sweep repeats each Community-1 setting five times (`__1`–`__5`) because results varied between identical runs, then runs Sortformer and four LS-EEND variants.
- `.build/release/fluidaudiocli sortformer <wav> --output <out.json>` runs Sortformer alone; `sortformer_to_segments.py <in> <out>` converts its JSON to `segments`.

## `experiments/mlx/run.py`

Whisper-format models through `mlx-whisper`, writing WhisperKit-shaped JSON with word timestamps. It is a `uv run` script with inline dependencies.

```bash
uv run experiments/mlx/run.py recording-16k.wav whisper.json mlx-community/whisper-large-v3-mlx zh
uv run experiments/mlx/run.py recording-16k.wav breeze.json eoleedi/Breeze-ASR-25-mlx zh
```

- Arguments: WAV, output path, Hugging Face repo, language (default `zh`). Decoding uses `condition_on_previous_text=False` to limit repetition loops.
- Set `HF_HUB_OFFLINE=1` when the models are already cached. The runner takes a repo name, not a revision; to match the pinned snapshots above, download them first with `hf download <repo> --revision <commit>`, or check `~/.cache/huggingface/hub/models--<org>--<name>/snapshots/`.
- Wrap in `/usr/bin/time -l` to record wall time and peak memory for the run spec.

Results from the [MLX follow-up](experiments/2026-10-24-transcription-variants.md#follow-up-whisper-and-breeze-through-mlx-2026-10-29) on 87 minutes of audio:

- Breeze-ASR-25 through MLX ran at about 0.22–0.25× real time (5.7 min for 22 min, 14.4 min for 65 min), against about 8× real time through transformers on MPS. Peak memory was 3.3–3.6 GB.
- Whisper Large v3 through MLX ran at about 0.12–0.14× real time with 2.6–3.6 GB peak memory.
- Breeze writes Traditional characters (0.1% of CJK characters change under OpenCC `s2tw`); Whisper's output had 14% that change, so it still needs conversion.

## `experiments/hushscribe-harness/`

Patch for HushScribe `51103f0c8f97344ec7ecdf6480a2ee53cd9a0e92` that runs one file import unattended with the language override and saves the diarizer's raw segments. Build and run steps are in its [README](../experiments/hushscribe-harness/README.md).

## `experiments/transcription/`

- `run_variants.sh` (env `WHISPERKIT_CLI`, `WHISPER_MODEL_DIR`, `AUDIO`, `OUT`): WhisperKit with Chinese forced vs. detection, VAD vs. none, SpeakerKit, and Turbo. Optional prompt runs read `MEETING_RECAP_CONTEXT_PROMPT` and `MEETING_RECAP_NAME_PROMPT`; keep those values out of the repository.
- `metrics.py <transcript.json>...`: proxy checks without a reference transcript. It counts Hangul or kana, segments with no CJK, stock hallucination phrases, the share of characters that change under `s2tw`, and optional expected terms from `MEETING_RECAP_EXPECTED_TERMS` (pipe-separated, kept private). Run with `uv run`.

## `experiments/full-recordings/run_full.sh`

Sortformer and WhisperKit Whisper Large v3 (Chinese forced, VAD, word timestamps) on whole recordings with `/usr/bin/time -l`. Env `WHISPERKIT_CLI`, `FLUIDAUDIO_CLI`, `WHISPER_MODEL_DIR`, `OUT`; arguments are WAV files.

## `experiments/breeze/run.py` and `experiments/pyannote/run.py`

`uv run` scripts with inline dependencies.

- `breeze/run.py <wav> <out.json>` runs Breeze-ASR-25 through transformers and writes WhisperKit-shaped JSON. It is slow on the M2 Pro; prefer the MLX runner.
- `pyannote/run.py <wav> <out.json> [num_speakers]` writes `segments`. It needs the Hugging Face terms accepted for `pyannote/speaker-diarization-community-1` and a logged-in token.

## Earlier findings

For an online Chinese + English call among three people on one mono track (2026-10-24 trial): forcing `language: zh` removed invented foreign-language lines; Sortformer separated speakers far better than Community-1 (29 of 30 turns vs. at most 19); both fit in under 1.6 GB peak memory. Treat these as a starting point, not a result for a different kind of recording.
