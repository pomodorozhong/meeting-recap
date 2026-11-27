# 2026-11-27: LFM3-Audio-2B as a voice for the synthetic collection

**Status:** complete

**Outcome:** Rejected. LFM3-Audio-2B's Chinese voice failed the collection's English-word gate on the handoff call, it has only one female and one male voice per language, and it sounded poor in an informal listen. The collection keeps its F5, Qwen and EmotiVoice voices ([decisions 8 and 9](../decisions.md)).

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `uv sync --frozen --project experiments/lfm3-audio`; the first run downloads the pinned model |
| Voice the fourteen scripts | `uv run --locked --project experiments/synthetic-call python experiments/synthetic-call/generate_lfm3.py "$OUT"` |
| Run the English-word gate | `uv run --locked --project experiments/synthetic-call python experiments/synthetic-call/check_voice.py "$OUT/handoff"` |

- **It needs:** nothing beyond the repository and the network for the first download.
- **It writes:** `OUT/<call>/` in the [collection's layout](../../experiments/synthetic-call/README.md#what-it-makes), plus `lfm3-report.json` per call and `voice-check.json` from the gate.
- **Takes about:** 12.8 minutes for all fourteen calls on the M2 Pro, plus the first download (about 4 GB).
- **By hand:** listening.
- **Expect to differ:** timings. Two runs of `handoff` on the same machine gave the same WAV bytes.

## Question

Would LFM3-Audio-2B's built-in voices be a better voice for the synthetic collection than the voices it uses?

- **Decision it informs:** whether to rebuild the collection with LFM3, or keep the voices in decisions 8 and 9.
- **Expected result:** none was written down before the runs. This summary was written after them, so it reports what was observed rather than testing a registered rule.
- **Builds on:** the [English-word gate](../../experiments/synthetic-call/README.md#voices-and-the-english-word-gate) that picked the F5 voice.

## Plan

- **Input:** the fourteen scripts of the 17-recording collection, unchanged: eight in Mandarin with English terms, six in English, one to four speakers.
- **Method:** [`generate_lfm3.py`](../../experiments/synthetic-call/generate_lfm3.py) voices every turn with [LFM3-Audio-2B MLX bf16](https://huggingface.co/LiquidAI/LFM3-Audio-2B-MLX-bf16) `452469a1` through MLX-VLM 0.8.1, then levels, times and mixes the turns exactly as `generate.py` does. Only the voices change. LFM3's TTS prompt names a language and a gender, `Perform TTS in <language> using a <female|male> voice.`, so each speaker gets the gender of their collection voice, with `Chinese` or `American English`. Sampling uses the model card's speech settings ([`tts_pins.json`](../../experiments/lfm3-audio/tts_pins.json)), seeded with seed 7 plus the turn index.
- **Checks:** the English-word gate on `handoff`, and an informal listen by the project owner. No structured listening review and no transcript scoring against the collection were run.

### Changes to the plan

None; no plan was committed before the runs.

## Results

| Check | LFM3 | F5 female voice (the collection's) |
| --- | --- | --- |
| Gate: standalone `log` recovered | No (heard as "Lock") | Yes |
| Gate: standalone `timeout` recovered | No (heard as "Time Pump") | Yes |
| Gate: Mandarin character agreement on the three checked turns | 83.3% | 97.9% |
| Gate verdict | **Fail** | Pass |

- **Voices:** one female and one male voice per language. Speakers of the same gender in a call get the same prompt, so 8 of the 14 calls (`script`, `design`, `logistics`, `onboarding`, `localization`, `english-design`, `english-committee`, `english-tabletop`) have speakers who may sound alike. That alone rules it out for a collection used to test speaker attribution.
- **Listening:** the project owner listened to the LFM3 calls, including `handoff` against the collection's version, and judged the voices poor. This was not a structured review.
- **Generation:** all fourteen calls, 33.4 minutes of audio, generated in 12.8 minutes at about 4.2 GB peak memory; every turn ended on its own before the token limit.

**Limits.** One gate call and one informal listen. The gate covers English terms in Mandarin speech only. Seeds other than 7 and the model's other sampling settings were not tried.

## Runtime and memory

Measured by the generator on the M2 Pro: 33.4 minutes of audio in 12.8 minutes of wall time, model loaded once per call; peak MLX memory 4.11–4.27 GB per call.

## Decision

Keep the collection's voices. LFM3-Audio-2B failed the gate that picked the F5 voice, can't give same-gender speakers distinct voices, and sounded poor. The generator stays in the repository so that a later LFM release can be voiced on the same scripts and compared with one command.

## Where this ran

- **Code:** the generator at the commit that adds this summary, on `feat/lfm3-asr`, not yet on `main`.
- **Models and weights:** `LiquidAI/LFM3-Audio-2B-MLX-bf16` at `452469a1afe66dd4932d0e9237603229fa606c0d`, license `lfm1.0`; Python packages pinned in [`uv.lock`](../../experiments/lfm3-audio/uv.lock). The gate used Whisper Large v3 MLX `49e6aa28`.
- **Machine:** M2 Pro, 16 GB; runs on 2026-11-27.
- **Kept outside the repository:** the generated audio.
