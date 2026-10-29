# 2026-10-24: Whisper (Chinese forced) and Sortformer on both full recordings

**Status:** complete. The combination fit in memory, ran faster than real time, and kept one label per person except for one voice split across two labels.

## Question

Does the combination chosen on the 10-minute excerpt, Whisper Large v3 with Chinese forced plus Sortformer, hold up on complete recordings in time, memory, and label stability?

## Input

Both parts of one online Chinese + English call among three people (Speakers A, B, and C), one mono track each: 22:23 and 64:49 (87 minutes in all), converted to 16 kHz mono WAV.

## Models and settings

| Step | Version | Settings |
| --- | --- | --- |
| Diarization | FluidAudio `ea500621819cadc46d6212af44624f2b45ab3240`, `fluidaudiocli sortformer` | defaults |
| Transcription | WhisperKit 0.18.0 `e2adabbe7d98dc4d0ab9a5b75424ecc42a9cdbef`, `openai_whisper-large-v3` | `--language zh --use-prefill-prompt --chunking-strategy vad --word-timestamps` |

Runner: [`experiments/full-recordings/run_full.sh`](../../experiments/full-recordings/run_full.sh). Host: Apple M2 Pro, 16 GB, macOS 26.6.2. Steps ran one after the other, with nothing else running.

## Runtime and memory

| Recording | Sortformer | Whisper |
| --- | --- | --- |
| 22:23 part | 551 s (0.41×), 0.96 GB peak | 271 s (0.20×), 1.19 GB peak |
| 64:49 part | 1,585 s (0.41×), 1.52 GB peak | 819 s (0.21×), 1.42 GB peak |

The 65-minute part took about 40 minutes for both steps. Memory pressure was not recorded.

## Scores

**Consistency with the excerpt.** Over the first 10 minutes of part 1, Sortformer agrees with its excerpt run for 95% of the time both runs label, and the attached text recovers 26 of 30 turns and 10 of 14 clips on the excerpt reference.

**Label stability.** The listener checked 20 more clips: five from a fourth label that appears in part 1 after 10:30, and three to five from each label in part 2, spread from start to end.

| Check | Result |
| --- | --- |
| Speaker A samples, part 2 (5, across the whole recording) | all on one label |
| Speaker B samples, part 2 (5, across the whole recording) | all on one label |
| Speaker C samples (10, both parts) | all Speaker C, spread over two labels in both parts; in part 1 the fourth label holds 24 s of Speaker C |
| After Speaker C left part 2 (at 23:22) | Speaker C's two labels hold 2.6 s in total |
| Excluded items | 0 |
| Label mapping | labels named from the listened samples |

**Metric limits.** 34 clips in all (14 on the excerpt, 20 here), named by one listener: they show the kind and rough frequency of errors, not an error rate or DER. Both recordings come from one call between the same three people, recorded by one app.

## Decision

For this kind of call, an online Chinese + English conversation among three people on one mono track, stop testing models. Build a pipeline from Sortformer, Whisper Large v3 with Chinese forced, attachment by overlap per word, a naming step that can give two labels the same name, and conversion to Traditional script. A split voice is repairable by naming; a merged one is not.

## Open questions

- Does a recording with the presenter's microphone on its own track remove the remaining presenter errors?
- How does Sortformer behave with more than four people, or several people in one room?
- Does the label split recur on other calls, and how often?
