# 2026-10-29: Sortformer on full calls, Breeze-ASR-25 vs. Whisper through MLX

**Status:** runs complete; listening review pending, so scores and the decision are not final.

## Question

1. Does Sortformer keep three speakers apart across two full recordings of one call, beyond the 10-minute excerpt reviewed in the 2026-10-24 trial?
2. Is Breeze-ASR-25 through MLX fast enough, and more accurate than Whisper Large v3 through MLX?

## Input

One online Chinese + English call among three people, recorded as one mono track in two parts: 22:23 and 64:49 (87 minutes in all). Models read 16 kHz mono WAV converted from the original media.

## Models and settings

| Run | Model and version | Settings |
| --- | --- | --- |
| Sortformer | FluidAudio `ea500621819cadc46d6212af44624f2b45ab3240`, `fluidaudiocli sortformer`; model `Sortformer_v2.1` (weight hashes in [docs/runners.md](../runners.md)) | defaults |
| Whisper | `mlx-community/whisper-large-v3-mlx` at `49e6aa286ad60c14352c404340ded53710378a11`, mlx-whisper 0.4.2 | `language=zh`, word timestamps, `condition_on_previous_text=False` |
| Breeze | `eoleedi/Breeze-ASR-25-mlx` at `172151e3fd93ab6dc841d639f23dd48b24bc8301`, mlx-whisper 0.4.2 | same as Whisper |
| Attachment | `attach.py --method word` | Sortformer labels attached to each ASR run per word |

Host: Apple M2 Pro, 16 GB, macOS 26.6.2. Runners are described in [docs/runners.md](../runners.md).

## Runtime and memory

| Run | 22:23 part | 65 min part | Peak memory |
| --- | ---: | ---: | ---: |
| Sortformer | 12.0 min (0.54×) | 30.4 min (0.47×) | 1.0–1.1 GB |
| Whisper Large v3 (MLX) | 2.6 min (0.12×) | 8.9 min (0.14×) | 2.6–3.6 GB |
| Breeze-ASR-25 (MLX) | 5.7 min (0.25×) | 14.4 min (0.22×) | 3.3–3.6 GB |

Every run overlapped another job (the `fluidaudiocli` build or the Sortformer runs), so these are upper bounds. Sortformer took 26 minutes for the 65-minute part when run alone on 2026-10-24.

Breeze-ASR-25 through transformers on MPS took 83 minutes for 10 minutes of audio (about 8× real time). Through MLX it runs at about 0.25× real time.

## Speaker labels

Sortformer produced four labels for three people on both parts. One label covers only 24 s (part 1) and 14 s (part 2) of speech, consistent with the 2026-10-24 finding that one voice is split across two labels.

## Transcript proxy checks

No reference transcript; from `experiments/transcription/metrics.py`.

| Run | CJK characters | Change under OpenCC `s2tw` | Hangul/kana | Segments with no CJK |
| --- | ---: | ---: | ---: | ---: |
| Whisper, part 1 | 2812 | 14.3% | 0 | 10 |
| Breeze, part 1 | 2889 | 0.1% | 0 | 4 |
| Whisper, part 2 | 8541 | 14.0% | 0 | 15 |
| Breeze, part 2 | 8598 | 0.1% | 0 | 5 |

Breeze writes Traditional characters directly; Whisper's output still needs `s2tw`. Segments with no CJK include legitimate English, so they are not all errors.

## Listening review

18 clips chosen with a fixed seed: 11 speaker-order clips (one per equal time bin across both parts, plus one per part on the rarely used fourth label; the 10 minutes reviewed before were skipped) and 7 transcript clips (where Whisper and Breeze disagree most after script normalization, plus one typical clip per part).

| Measure | Result |
| --- | --- |
| Sortformer turns recovered | pending |
| Sortformer clips correct | pending |
| Excluded items (unsure, skipped, unusable, unreviewed) | pending |
| Label mapping | best mapping fitted to the reference (default) |
| Transcript comparison | pending |

**Metric limits.** Speaker order is measured on selected clips only: it is not DER, not transcript accuracy, and not an error rate for the whole recording. The default mapping is fitted to the reference, which flatters each run.

## Decision

Pending the listening review. Already settled: speed no longer rules out Breeze-ASR-25.

## Open questions

- Does the rarely used fourth label belong to the same person as before, and can a naming step merge it?
- Does Sortformer's accuracy hold up past the first 10 minutes?
- Should Breeze replace Whisper in the pipeline candidate? It would also remove the `s2tw` step.
- Do word-level labels from attachment score differently from Sortformer's own segments?
