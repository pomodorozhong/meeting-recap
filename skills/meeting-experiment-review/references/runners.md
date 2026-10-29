# Runners

Scripts that produced the original experiments. Each writes to a scratch `OUT` directory; register the outputs with `dataset.py add-run` afterwards. All were run on macOS 26.6.2, Apple M2 Pro, 16 GB, Swift 6.3.3.

| Component | Pinned version |
| --- | --- |
| WhisperKit / `whisperkit-cli` | 0.18.0, `e2adabbe7d98dc4d0ab9a5b75424ecc42a9cdbef` |
| FluidAudio / `fluidaudiocli` | `ea500621819cadc46d6212af44624f2b45ab3240` |
| Whisper model | `argmaxinc/whisperkit-coreml/openai_whisper-large-v3` |
| Breeze-ASR-25 | `MediaTek-Research/Breeze-ASR-25` at `cffe7ccb404d025296a00758d0a33468bec3a9d0` |

Input audio for all runners: 16 kHz mono WAV.

## `diarization/`

Swift package `diarexp` for FluidAudio's offline (Community-1) diarizer, plus a sweep script.

```bash
cd scripts/runners/diarization
swift build -c release && swift build -c release --product fluidaudiocli
AUDIO=excerpt-16k.wav OUT=/scratch/dia ./run_sweep.sh
```

- `diarexp <wav> <out.json> [key=value ...]` writes `segments` JSON directly. Keys: `num`, `min`, `max`, `thr`, `minseg`, `excl`, `exovl`, `step`, `mingap`, `fa`, `fb`.
- The sweep repeats each Community-1 setting five times (`__1`–`__5`) because results varied between identical runs, then runs Sortformer and four LS-EEND variants.
- `sortformer_to_segments.py <in> <out>` converts `fluidaudiocli` JSON to `segments`.

## `transcription/`

- `run_variants.sh` (env `WHISPERKIT_CLI`, `WHISPER_MODEL_DIR`, `AUDIO`, `OUT`): Chinese forced vs. detection, VAD vs. none, SpeakerKit, Turbo. Optional prompt runs read `MEETING_RECAP_CONTEXT_PROMPT` and `MEETING_RECAP_NAME_PROMPT`; keep those values out of the repo.
- `metrics.py <report.json>...`: proxy checks (see SKILL.md).

## `full-recordings/run_full.sh`

Sortformer and Whisper Large v3 (Chinese forced, VAD, word timestamps) on whole recordings with `/usr/bin/time -l` for wall time and peak memory. Env `WHISPERKIT_CLI`, `FLUIDAUDIO_CLI`, `WHISPER_MODEL_DIR`, `OUT`; arguments are WAV files.

## `breeze/run.py` and `pyannote/run.py`

`uv run` scripts with inline dependencies.

- `breeze/run.py <wav> <out.json>` writes WhisperKit-shaped JSON. Slow through transformers on MPS (about 8× real time on the M2 Pro).
- `pyannote/run.py <wav> <out.json> [num_speakers]` writes `segments`. Needs the Hugging Face terms accepted for `pyannote/speaker-diarization-community-1` and a logged-in token.

## Prior findings

For an online Chinese + English call among three people on one mono track: forcing `language: zh` removed invented foreign-language lines; Sortformer separated speakers far better than Community-1 (29 of 30 turns vs. at most 19); both fit in under 1.6 GB peak memory. Treat these as a starting point, not a result for a different kind of recording.
