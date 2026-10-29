# 2026-10-29: Sortformer on full calls, Breeze-ASR-25 vs. Whisper through MLX

**Status:** review pending. Runs are complete; scores and the decision wait for the listening review.

This experiment ran before summaries were registered ahead of time; the goal, plan, and review sections were added afterwards in the same form.

## Question

1. Does Sortformer keep three speakers apart across two full recordings of one call, beyond the 10-minute excerpt reviewed in the 2026-10-24 trial?
2. Is Breeze-ASR-25 through MLX fast enough, and more accurate than Whisper Large v3 through MLX?

## Goal and assumptions

- **Decision it informs:** whether Sortformer stays the diarizer for saved recordings, and whether the pipeline candidate uses Breeze-ASR-25 or Whisper Large v3 for transcription.
- **Builds on:** the [diarizer comparison](2026-10-24-diarizer-comparison.md) (Sortformer 29 of 30 turns on the first 10 minutes), the [full-recording run](2026-10-24-full-recordings.md) (one voice split across two labels), and the [transcription variants](2026-10-24-transcription-variants.md) (Breeze cleanest, but about 8× real time through transformers).
- **Assumptions:** the same kind of call as before (three people, Chinese + English, one mono track, online); the listener names speakers consistently across both parts; MLX models are cached; Whisper and Breeze through MLX decode like their WhisperKit and transformers counterparts.
- **Expected result:** Sortformer keeps most turns past the first 10 minutes, with one voice still split; Breeze runs near real time or faster through MLX and is at least as accurate as Whisper. Sortformer missing many turns later in the call, or Breeze transcribing worse than Whisper in the listened clips, would change the decision.

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

## Plan

| Run ID | Model and pinned version | Command (from the repository root; WAVs in a scratch folder) |
| --- | --- | --- |
| `sortformer-part1`, `sortformer-part2` | Sortformer, see above | `experiments/diarization/.build/release/fluidaudiocli sortformer part1.wav --output sortformer_part1.json`, then `python3 experiments/diarization/sortformer_to_segments.py sortformer_part1.json sortformer_part1_seg.json` |
| `whisper-mlx-part1`, `whisper-mlx-part2` | Whisper Large v3 (MLX), see above | `HF_HUB_OFFLINE=1 /usr/bin/time -l uv run experiments/mlx/run.py part1.wav whisper_part1.json mlx-community/whisper-large-v3-mlx zh` |
| `breeze-mlx-part1`, `breeze-mlx-part2` | Breeze-ASR-25 (MLX), see above | `HF_HUB_OFFLINE=1 /usr/bin/time -l uv run experiments/mlx/run.py part1.wav breeze_part1.json eoleedi/Breeze-ASR-25-mlx zh` |
| `whisper-sortformer-part1`, `breeze-sortformer-part1`, and the same for part 2 | `attach.py --method word` | `python3 .agents/skills/meeting-experiment-review/scripts/attach.py "$MEETING_REVIEW_DATA" --asr-run whisper-mlx-part1 --diarization-run sortformer-part1 --id whisper-sortformer-part1` |

Recording IDs `part1` (22:23) and `part2` (64:49), group `call-2026-10-22`. Each output is registered with `dataset.py add-run` under the run ID shown.

Clip selection (`uv run .agents/skills/meeting-experiment-review/scripts/pick_clips.py "$MEETING_REVIEW_DATA" --config select.json --out plan.json`):

```json
{"id": "full-calls-2026-10-29", "seed": 20261029, "normalize": "first",
 "question": "Does Sortformer keep the three speakers apart across both full recordings, and is Breeze-ASR-25 (MLX) more accurate than Whisper Large v3 (MLX)?",
 "recordings": [
  {"recording_id": "part1", "skip_before": 600, "diarization_run": "sortformer-part1", "speaker_clips": 4,
   "speaker_show_runs": ["sortformer-part1", "whisper-sortformer-part1"],
   "transcript_runs": ["whisper-mlx-part1", "breeze-mlx-part1"], "transcript_clips": 2},
  {"recording_id": "part2", "diarization_run": "sortformer-part2", "speaker_clips": 7,
   "speaker_show_runs": ["sortformer-part2", "whisper-sortformer-part2"],
   "transcript_runs": ["whisper-mlx-part2", "breeze-mlx-part2"], "transcript_clips": 3}]}
```

Review session ID: `full-calls-2026-10-29`. Reference ID: `ref-full-calls-2026-10-29`. Evaluation IDs: `eval-full-calls-2026-10-29-part1`, `eval-full-calls-2026-10-29-part2`.

## Run the review

```bash
python3 .agents/skills/meeting-experiment-review/scripts/review.py serve "$MEETING_REVIEW_DATA" --session full-calls-2026-10-29 --port 8770
```

Run from the repository root with `MEETING_REVIEW_DATA` set to the private dataset. Open the `http://127.0.0.1:8770/?token=…` URL it prints; answers save as you go, and Ctrl-C stops the server. Use the same speaker IDs for each person in every clip. For the 15 s transcript clips, saving **unsure** with a note on which run is closer is fine. Click **Finish session** when done.

## Restart from scratch

If the private data is lost: register both recordings again as `part1` and `part2`, convert them to 16 kHz mono WAV, rerun the commands in the plan, register the runs under the same IDs, and rerun `pick_clips.py` with the config above. The same seed gives the same 18 clips only if the runs reproduce the same segments and text; otherwise review the new plan before preparing the session.

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
