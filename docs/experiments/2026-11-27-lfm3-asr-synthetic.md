# 2026-11-27: LFM3-Audio-2B transcription on the synthetic collection

**Status:** planned

**Outcome:** pending.

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

Pending.

## Runtime and memory

Pending.

## Decision

Pending.

## Where this ran

- **Code:** the runner in [`experiments/lfm3-audio/`](../../experiments/lfm3-audio/), at the commit that adds this summary.
- **Models and weights:** `LiquidAI/LFM3-Audio-2B-MLX-bf16` at `452469a1afe66dd4932d0e9237603229fa606c0d`, license `lfm1.0`. Python packages are pinned in [`uv.lock`](../../experiments/lfm3-audio/uv.lock).
- **Machine:** M2 Pro, 16 GB.
- **Kept outside the repository:** the fixtures and the run outputs.
