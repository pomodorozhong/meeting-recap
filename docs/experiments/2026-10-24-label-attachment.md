# 2026-10-24: Attaching speaker labels to transcript text

**Status:** complete. The attachment method changed the score by at most one turn on this input.

## Question

A diarizer produces a timeline; a transcript needs each piece of text tied to a label. How much does the attachment method matter, and how much does attaching text cost compared with the diarizer's own segments?

## Input

The same 10:00 excerpt of a three-person Chinese + English call (Speakers A, B, and C), 16 kHz mono WAV.

## Models and settings

| Step | Version | Settings |
| --- | --- | --- |
| Transcription | WhisperKit 0.18.0 `e2adabbe7d98dc4d0ab9a5b75424ecc42a9cdbef`, `openai_whisper-large-v3` | `--language zh --use-prefill-prompt --chunking-strategy vad --word-timestamps` |
| Diarization | FluidAudio `ea500621819cadc46d6212af44624f2b45ab3240` Sortformer | defaults |
| Attachment | the original `attach.py`, now the skill's `attach.py` | `line`, `seg`, `word` |

Host: Apple M2 Pro, 16 GB, macOS 26.6.2.

## Runtime and memory

Attachment is a few lines of Python over two JSON files and takes well under a second. Transcription and diarization costs are in the [transcription](2026-10-24-transcription-variants.md) and [diarizer](2026-10-24-diarizer-comparison.md) summaries.

## Scores

Same 14-clip, 30-turn listening reference as the diarizer comparison; Sortformer alone scores 29 turns and 12 clips.

| Method | Turns recovered | Clips correct |
| --- | ---: | ---: |
| One label per segment, looked up at its end second (like HushScribe) | 26 | 11 |
| One label per segment, by largest overlap | 27 | 11 |
| One label per word, by largest overlap | 27 | 11 |

| Measure | Value |
| --- | --- |
| Excluded items | 0 |
| Label mapping | best mapping fitted to the reference, per run |

Attaching text costs two turns compared with the diarizer alone, probably because a few short replies have no transcribed word inside the diarizer's segment.

**Metric limits.** Selected-clip speaker order only; not DER, transcript accuracy, or an error rate for the recording. The fitted mapping flatters each run.

## Decision

Attach by overlap, per word where word timestamps exist. The method matters little with WhisperKit's short segments, but HushScribe's longer chunks, labeled at the moment their text appears, make its single-second lookup worse than this test shows, so that step should change in any HushScribe-based pipeline.

## Open questions

- Does attachment cost more turns with longer ASR segments, such as those produced by prompts or other runtimes?
