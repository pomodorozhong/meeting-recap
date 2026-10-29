# 2026-10-24: Diarizer settings and models on a 10-minute excerpt

**Status:** complete. Sortformer recovered 29 of 30 reference turns; no Community-1 setting got past 19.

## Question

The [HushScribe trial](2026-10-24-hushscribe-trial.md) merged three voices under one label. Does a known speaker count or another Community-1 setting fix that, and do other local diarizers do better on the same excerpt?

## Input

The same 10:00 excerpt of a three-person Chinese + English call (Speakers A, B, and C), one mono track, converted with ffmpeg to 16 kHz mono WAV.

## Models and settings

| Diarizer | Version | Settings |
| --- | --- | --- |
| Community-1 (`OfflineDiarizerManager`) | FluidAudio `ea500621819cadc46d6212af44624f2b45ab3240`, via `experiments/diarization` `diarexp` | defaults, then the sweep below; five runs per setting |
| LS-EEND | same FluidAudio, `fluidaudiocli lseend` | variants `dihard3`, `ami`, `callhome`, `dihard2` |
| Sortformer | same FluidAudio, `fluidaudiocli sortformer` | defaults; repeated once |
| SpeakerKit | WhisperKit 0.18.0 `e2adabbe7d98dc4d0ab9a5b75424ecc42a9cdbef` | `--diarization --diarization-num-speakers 3`, inside a Whisper Large v3 transcription run |

Host: Apple M2 Pro, 16 GB, macOS 26.6.2. Runners are described in [docs/runners.md](../runners.md).

## Runtime and memory

| Diarizer | Time for 600 s | Peak memory |
| --- | ---: | ---: |
| Community-1 | about 6 s | not recorded |
| LS-EEND | about 12 s | not recorded |
| SpeakerKit (with transcription) | 167 s | 1.5 GB |
| Sortformer | 267 s (about 2.4× faster than real time) | 0.83 GB footprint |

Sortformer's timing suggests it runs mostly on the CPU.

## Scores

Reference: 14 clips around speaker changes, named by one listener, 30 turns in all, with 1 s padding.

**Community-1 settings** (range over five runs):

| Setting | Turns recovered | Clips correct |
| --- | --- | --- |
| Defaults | 12 every run | 1 |
| Three speakers | 15–18 | 4–6 |
| Three speakers, overlapping speech kept (`exclusiveSegments = false`) | 16–19 | 5–7 |
| Three speakers, minimum embedding duration 0.25 s | 15–19 | 3–6 |
| Three speakers, both changes above | 19 every run | 2–4 |
| Three speakers, overlap excluded from embeddings off, or minimum 0.5 s | 15–18 | 3–6 |
| No count, clustering threshold 0.7 or 0.8 | 17 every run | 6 |
| No count, 2–5 speakers | 13–15 | 4–6 |

Thresholds of 0.3–0.55 merged everyone into one or two labels; 0.7–0.8 produced four or five labels with a few seconds each. A fixed speaker count gave different results from identical runs.

With three speakers, each label followed one person in the first run checked: long turns and clean handovers were correct, and short questions, reactions, and agreements were absorbed into the longest speaker's label.

**Other diarizers:**

| Diarizer | Turns recovered | Clips correct | Notes |
| --- | ---: | ---: | --- |
| Community-1, defaults | 12 | 1 | What HushScribe uses |
| LS-EEND, four variants | 20–25 | 4–5 | Labels flip often within one person's speech |
| SpeakerKit, three speakers | 24 | 9 | |
| **Sortformer** | **29** | **12** | Identical output on a repeat run |

Sortformer missed one turn and added one stray turn. Over the first 75 s it gave 0.4 s of a 42.5 s presentation to another label. It tracks at most four speakers.

| Measure | Value |
| --- | --- |
| Excluded items | 0 (all 14 clips answered) |
| Label mapping | best mapping fitted to the reference, per run |

**Metric limits.** Turns recovered is the longest common subsequence of predicted and reference speaker order inside each clip; a clip is correct when every turn appears, nobody absent is labeled, and no extra turn appears unless the listener heard further short exchanges. A run with one label for everyone still recovers about 12 of 30. This is selected-clip speaker order, not DER or an error rate for the recording, and the fitted mapping flatters each run.

## Decision

Use Sortformer for this kind of call. Community-1's misses on short turns are a limit of the model on this input, not a setting left at the wrong value.

## Open questions

- The original pyannote Community-1 pipeline could not be run (gated model terms not accepted). It would show whether the default's failure belongs to the model or to FluidAudio's conversion.
- Sortformer's four-speaker limit and CPU-bound speed for longer or larger meetings.
