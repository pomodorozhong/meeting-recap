# 2026-11-27: LFM3-Audio-2B transcription on the synthetic collection

**Status:** complete

**Outcome:** With the language declared, LFM3 had a lower Mandarin error rate than the full Whisper component baseline (7.27% against 9.27%) and a slightly higher English one (2.01% against 1.88%), so under the rule set before the run it is a candidate for Mandarin only. Most of its Mandarin lead comes from the two calls with long pauses, where whole-call Whisper inserts text; Whisper and Turbo with the existing digital-pause split both beat it there. It writes only Simplified Chinese and gives no word timestamps. The current recognizers stay, and #27 closes.

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `uv sync --frozen --project experiments/lfm3-audio`; the first run downloads the pinned model |
| Run one configuration | `uv run --frozen --project experiments/lfm3-audio python experiments/lfm3-audio/run.py "$FIXTURES" "$RUNS/lfm3-declared" --prompt declared` (and `"$RUNS/lfm3-auto" --prompt auto`) |
| Score a run without models | `uv run --locked --project experiments/synthetic-call python experiments/synthetic-call/score_transcripts.py "$FIXTURES" "$RUNS/lfm3-declared" --output lfm3-declared-scores.json` |

- **It needs:** `FIXTURES`, the verified collection built by [`collection.py`](../../experiments/synthetic-call/README.md#seventeen-recording-collection). The runner refuses a folder whose audio or scripts differ from the committed collection hashes.
- **It writes:** `RUNS/<run>/<call>/asr.json` for the fourteen scripted calls, each with its text, its windows, the audio and script hashes, the model pin, the settings and its timing. Calls with a report are skipped.
- **By hand:** nothing.
- **Expect to differ:** timings. Decoding is greedy, so text should repeat on the same machine and MLX build.

## Question

Is LFM3-Audio-2B a useful transcriber for this project's Mandarin calls with English terms, and for English calls, compared with the recognizers already measured on the same audio? This is the synthetic step of [#27](https://github.com/pomodorozhong/meeting-recap/issues/27); the real-call excerpt that issue asks for is not part of it.

- **Decision it informs:** whether LFM3 earns the real-call comparison in #27, or #27 closes with the current baseline kept.
- **Expected result:** LFM3 is worse than full Whisper on Mandarin with English terms, because it writes Simplified Chinese and, in an informal check on LFM3-voiced audio, misheard English product terms. It may be close on English.
- **Builds on:** the [recognizer comparison on the same collection](2026-11-02-synthetic-collection-recognition.md) and its [full Whisper component baseline](../../experiments/synthetic-call/reference/transcript-baseline.json).

## Plan

- **Input:** the fourteen scripted calls of the hash-verified 17-recording synthetic collection: eight in Mandarin with English terms and six in English, one to four speakers, 0.8 to 5.1 minutes each, 31.9 minutes in all. The two remixes and the silence control are left out, as in the recognizer comparison's language scores.
- **Assumptions:** one M2 Pro with 16 GB, serial local inference, nothing else heavy running during the runs. The reference is the intended script, not a listening judgment.

| Run ID | Model and pinned version | Settings |
| --- | --- | --- |
| `lfm3-declared` | [LFM3-Audio-2B MLX bf16](https://huggingface.co/LiquidAI/LFM3-Audio-2B-MLX-bf16) `452469a1`, MLX-VLM 0.8.1 | System prompt `Perform ASR in Chinese.` or `Perform ASR in English.`, from the script's declared language |
| `lfm3-auto` | Same | System prompt `Perform ASR.` |

Both runs decode greedily (temperature 0), at most 1,024 tokens per window. LFM3 stopped after about a minute of text on a 5.5-minute call in a check before this plan (on LFM3-voiced audio, not the collection), so each call is cut into windows of at most 30 s. Each cut falls at the quietest 0.1 s of the last 5 s of its window, chosen from the audio alone, never from the reference turns. Window texts are joined with no separator in Mandarin and a space in English.

Scoring uses [`score_transcripts.py`](../../experiments/synthetic-call/score_transcripts.py) as the recognizer comparison did: English word error rate (WER) after the Whisper English normalizer, Mandarin character error rate (CER) after OpenCC conversion to Simplified and removal of punctuation and spaces. So the scores don't count LFM3's Simplified output as errors; whether the raw output is Traditional is reported separately.

The comparison points are the published scores on the same audio: full Whisper component baseline 1.88% WER and 9.27% CER (no word timestamps, temperature zero), and, with word timestamps, full Whisper 2.18% and 9.98%, Turbo 1.98% and 7.59%, Breeze 7.43% and 12.08%.

**Decision rule**, set before the runs:

- If the better LFM3 configuration is no worse than the full Whisper component baseline in both languages (WER ≤ 1.88% and CER ≤ 9.27%), LFM3 goes on to #27's real-call excerpt.
- If it is better in one language and worse in the other, report it as a candidate for that language only, and #27 decides whether a language-specific recognizer is worth its cost.
- Otherwise, keep the current recognizers. #27 then closes after this summary and a note on timing (below), without the real-call comparison.

Also recorded: total decode time and real-time factor per run, cold model load, peak MLX memory, windows that hit the token limit, whether output is Traditional or Simplified, and the timing LFM3 gives. It gives none below the window: there are no word timestamps, so attaching Sortformer labels by word overlap would need a separate aligner, which #27 puts out of scope.

### Changes to the plan

None.

## Results

All 28 call reports completed, and no window hit the token limit. Scores are from `score_transcripts.py`; an edit is one inserted, deleted or substituted word in English or character in Mandarin, and lower is better.

| Recognizer | English WER (6 calls; 3,028 words) | Mandarin CER (8 calls; 3,095 characters) |
| --- | ---: | ---: |
| `lfm3-declared` | 2.01% (61) | 7.27% (225) |
| `lfm3-auto` | 2.15% (65) | 8.17% (253) |
| Full Whisper component baseline, no word timestamps | **1.88% (57)** | 9.27% (287) |
| Full Whisper, word timestamps | 2.18% (66) | 9.98% (309) |
| Turbo Q4, word timestamps | 1.98% (60) | 7.59% (235) |
| Full Whisper, digital-pause split | 2.08% (63) | **6.43% (199)** |
| Turbo Q4, digital-pause split | 1.98% (60) | 6.56% (203) |

The rows other than LFM3's are the published scores on the same audio, from the [recognizer comparison](2026-11-02-synthetic-collection-recognition.md), its [results file](2026-11-02-synthetic-collection-results.json) and the [component baseline](../../experiments/synthetic-call/reference/transcript-baseline.json). The pause-split rows come from the [silence summary](2026-11-02-synthetic-collection-silence.md); they were not in this plan's rule, but they are the fairer comparison, because LFM3's windows also split each call.

Per call, `lfm3-declared` against the component baseline (edits):

| Call | LFM3 | Whisper | Call | LFM3 | Whisper |
| --- | ---: | ---: | --- | ---: | ---: |
| script | 106 | 64 | english-audit | 13 | 13 |
| handoff | 13 | 16 | english-handoff | 5 | 8 |
| logistics | 22 | 28 | english-design | 3 | 5 |
| stocktake | 16 | 48 | english-tabletop | 6 | 7 |
| scheduling | 12 | 9 | english-committee | 20 | 13 |
| design | 22 | 20 | english-training | 14 | 11 |
| onboarding | 21 | 89 | | | |
| localization | 13 | 13 | | | |

LFM3 made fewer edits on seven calls and more on five. In Mandarin, `stocktake` (an 18-second pause) and `onboarding` (a 12-second pause) account for 137 of Whisper's edits against 37 of LFM3's. On the other six Mandarin calls LFM3 made 188 edits against Whisper's 150, mostly on the 73-turn `script` call.

The declared prompt was better than `Perform ASR.` in both languages. Every Mandarin output was in Simplified script: 769 characters that have a different Traditional form, and no Traditional-only characters. LFM3 gives text per window only, so its timing is no finer than the 25–30 s windows.

**Limits.** Synthetic speech from scripts, scored against the script, not a listener. One run of each configuration. The two long pauses favour any method that splits the audio, and the plan's rule compared LFM3's windows with whole-call Whisper. Nothing here tests real calls, overlapping speech in a room, or speaker attribution.

## Runtime and memory

Measured by the runner on the M2 Pro, with the model loaded once per run (2.1 s from the cache): decoding the 31.9 minutes took 151.6 s for `lfm3-declared` and 149.9 s for `lfm3-auto`, a real-time factor of about 0.08. Each whole run took about 155 s of wall time by `/usr/bin/time`. Peak MLX allocations were 4.3 GB; that counts MLX's own memory only, not the whole process. The published wall times on the same calls were 316 s for full Whisper and 166 s for Turbo, but each of those launched a process and loaded the model per call, so they are not a like-for-like comparison.

Peak memory measured like the published figures, after the runs on 2026-11-27: one Python process per call (`lfm3-declared` settings, model loaded in that process), with the peak memory footprint from `/usr/bin/time -l`. The other columns are the saved figures from the [recognizer comparison](2026-11-02-synthetic-collection-recognition.md#runtime-and-memory) on the same calls.

| Call (length) | LFM3 | Full Whisper | Turbo Q4 | Breeze |
| --- | ---: | ---: | ---: | ---: |
| `script` (5.5 min) | 5.06 GB | 9.00 GB | 4.16 GB | 13.43 GB |
| `english-training` (3.4 min) | 5.08 GB | 7.46 GB | 3.35 GB | 11.96 GB |
| `handoff` (0.9 min) | 4.98 GB | 6.26 GB | 2.27 GB | 7.95 GB |
| `stocktake` (0.8 min) | 4.89 GB | 5.53 GB | 2.04 GB | 6.84 GB |

LFM3's peak stays near 5 GB because it only sees one window of at most 30 s; the others take the whole file, and their peaks grow with the call. On the longest call LFM3 used about half of full Whisper's peak, and Turbo still used the least. Real calls of 20–65 minutes were not measured.

## Decision

Under the rule set before the run, LFM3 is a candidate for Mandarin only: it beat the component baseline in Mandarin (7.27% ≤ 9.27%) and missed it in English (2.01% > 1.88%). The rule left to #27 whether a Mandarin-only recognizer is worth its cost. On 2026-11-27 the project owner decided it isn't: the pause-split Whisper and Turbo runs already do better in Mandarin, LFM3's lead comes from the two long-pause calls, and it would need Traditional conversion and a separate aligner for speaker labels. Keep the current recognizers; LFM3 is not added to the pipeline, and #27 closes without the real-call excerpt.

## Open questions

- Would Whisper with the same quiet-point windows match LFM3's gain on the long-pause calls? That would separate the windowing from the model.

## Where this ran

- **Code:** both runs used commit `5014068`, which adds the plan and the runner; it is on `feat/lfm3-asr`, not yet on `main`.
- **Models and weights:** `LiquidAI/LFM3-Audio-2B-MLX-bf16` at `452469a1afe66dd4932d0e9237603229fa606c0d`, license `lfm1.0`. Python packages are pinned in [`uv.lock`](../../experiments/lfm3-audio/uv.lock).
- **Machine:** M2 Pro, 16 GB; MLX-VLM 0.8.1 with the MLX build in its lock; runs on 2026-11-27.
- **Kept outside the repository:** the fixtures and the run outputs.
