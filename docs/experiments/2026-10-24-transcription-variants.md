# 2026-10-24: Transcription settings and models on a 10-minute excerpt

**Status:** complete. Forcing Chinese removed invented foreign-language lines; Breeze-ASR-25 had the cleanest text but was too slow through transformers.

## Question

The [HushScribe trial](2026-10-24-hushscribe-trial.md) produced invented foreign-language lines, misheard names, and mixed scripts. Which language setting, prompt, or model gives the most usable Chinese + English transcript on the target Mac?

## Input

The same 10:00 excerpt of a three-person Chinese + English call, 16 kHz mono WAV.

## Models and settings

All WhisperKit runs used WhisperKit 0.18.0 `e2adabbe7d98dc4d0ab9a5b75424ecc42a9cdbef` with `--use-prefill-prompt --word-timestamps` and VAD chunking unless noted ([`experiments/transcription/run_variants.sh`](../../experiments/transcription/run_variants.sh)).

| Run | Model | Settings |
| --- | --- | --- |
| Trial | Large v3 in HushScribe | language detected per HushScribe chunk |
| Chinese forced | `openai_whisper-large-v3` | `--language zh` |
| Detected per window | `openai_whisper-large-v3` | no language |
| Context prompt | `openai_whisper-large-v3` | `--language zh` plus a prompt naming the people and terms |
| Names prompt | `openai_whisper-large-v3` | `--language zh` plus a prompt with the two guests' names only |
| No VAD | `openai_whisper-large-v3` | `--language zh`, no chunking strategy |
| SpeakerKit | `openai_whisper-large-v3` | `--language zh`, `--diarization --diarization-num-speakers 3` |
| Turbo | `large-v3-v20240930_turbo` | `--language zh` |
| Breeze | `MediaTek-Research/Breeze-ASR-25` at `cffe7ccb404d025296a00758d0a33468bec3a9d0`, transformers on MPS | `language=zh`, 30 s chunks, word timestamps ([`experiments/breeze/run.py`](../../experiments/breeze/run.py)) |

Prompt texts are private and are read from environment variables, not stored in the repository. Host: Apple M2 Pro, 16 GB, macOS 26.6.2.

## Runtime and memory

| Run | Time for 600 s | Peak memory |
| --- | ---: | ---: |
| Trial (HushScribe) | 241 s | not recorded |
| Chinese forced | 184 s | 1.2 GB |
| SpeakerKit (with diarization) | 167 s | 1.5 GB |
| Breeze through transformers | about 83 min | not recorded |

Other runs were not timed separately.

## Results

No reference transcript; runs were compared with proxy checks ([`experiments/transcription/metrics.py`](../../experiments/transcription/metrics.py)) and by reading known passages side by side.

| Run | Result |
| --- | --- |
| Trial | Six invented lines in Norwegian, Korean, German, or English; about 5% Simplified characters |
| **Chinese forced** | No invented foreign lines, one stock phrase; 9% Simplified characters |
| Detected per window | Detected English for the opening and translated most of the first three minutes into English, with scattered English lines until about 06:25 |
| Context prompt | Kept only 257 CJK characters instead of about 1,440, and invented filler |
| Names prompt | Names mostly right and 2% Simplified, but dropped passages and attributed a remark to the wrong person; longer segments lowered speaker attachment to 24 of 30 turns |
| Turbo | 21% Simplified; speaker attachment 26 of 30 turns, 9 of 14 clips |
| Breeze | Cleanest text: Traditional throughout, no invented lines, and correct where Whisper misheard a UI term |

| Measure | Value |
| --- | --- |
| Excluded items | not applicable (no listening reference for text) |
| Label mapping | best mapping, for the attachment scores quoted above |

**Metric limits.** The checks need no reference: share of CJK characters that change under OpenCC `s2tw`, lines with no CJK, stock phrases Whisper invents in silence, and passages read side by side. They do not measure a character error rate.

## Decision

Force Chinese. It removes invented foreign lines without the omissions prompts cause, and English product terms still come through. Convert Simplified characters after transcription, and fix names in a naming step after speaker separation rather than through a prompt. Breeze-ASR-25 needs a faster runtime before it can replace Large v3.

## Open questions

- Can Breeze-ASR-25 run fast enough after a Core ML or MLX conversion? (Answered on [2026-10-29](2026-10-29-full-calls-sortformer-breeze-mlx.md): about 0.25× real time through MLX.)
- What is the character error rate on a few minutes with a hand-made reference transcript?
