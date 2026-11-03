# 2026-11-02: recognizers and spoken language on the 17-recording synthetic collection

**Status:** complete

**Outcome:** Declaring the spoken language improved all six English calls. Turbo was the fastest recognizer on every spoken recording and had the lowest error rate of the three in both languages, but full Whisper made fewer edits on six calls, and most of Turbo's Mandarin lead comes from one call. Full Whisper stays the default because this synthetic evidence doesn't justify switching before the private listening review, not because it won. Turbo is offered as an option.

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/synthetic-call/collection_setup.sh` |
| Run everything | `experiments/synthetic-call/collection_run.sh "$FIXTURES" "$RESULTS"` |
| Rerun this summary's step | `experiments/synthetic-call/collection_run.sh "$FIXTURES" "$RESULTS" --step decode` |
| Check saved results without models | `uv run --project experiments/synthetic-call experiments/synthetic-call/collection_scores.py "$FIXTURES" "$RESULTS" > scores.json` |

- **It needs:** `FIXTURES`, the verified collection built by [`collection.py`](../../experiments/synthetic-call/README.md#seventeen-recording-collection), and `RESULTS`, a new absolute path outside Git.
- **It writes:** every model output under `RESULTS`, with the measurements in `RESULTS/scores.json`. This is one run shared by [several summaries](../../experiments/synthetic-call/README.md#compare-the-pipeline-on-this-collection), so the scorer needs every step's outputs. [The saved measurements](2026-11-02-synthetic-collection-results.json) are the committed copy.
- **Takes about:** 24 minutes for this summary's `decode` step, in the saved timings. The whole run takes about 54 minutes, plus the untimed `turns` and `replays` steps.
- **By hand:** nothing for this summary.
- **Expect to differ:** timings on any rerun, and possibly model text on another machine. The scorer recalculates the measurements from saved outputs, so it should match the committed file byte for byte.

## Question

Is Turbo always as accurate as full Whisper, and faster? Does Breeze win on sparse speech? Does declaring the spoken language help English calls?

- **Decision it informs:** which recognizer stays the default, which are offered, and whether language must be specified.
- **Expected result:** declaring English improves WER. Keep Mandarin as the default language, and expose language explicitly if declaring it wins.
- **Builds on:** a [seven-recording trial](https://github.com/pomodorozhong/meeting-recap/blob/c714e05/docs/experiments/2026-11-01-synthetic-collection.md) in draft PR #31, which is **not on `main`**. This experiment tests its claims on a larger collection.

## Plan

- **Input:** all 17 hash-verified mono fixtures in the collection at `4c8c2f0`: fourteen independent scripts (eight Mandarin including English terms, six English; one to four speakers), two remixes reported separately, and digital silence.
- **Assumptions:** one M2 Pro with 16 GB, serial local inference. Generated text is the known intended speech, not a listener judgment. The trial used some of the same scripts, but synthesis and voices have changed since, so only matching audio hashes are exact replications.

| Run ID | Model and pinned version | Settings |
| --- | --- | --- |
| `whisper` | Full Whisper `49e6aa28` | Script's declared language, `zh` for controls |
| `turbo` | Turbo Q4 `660c343b` | Same |
| `breeze` | Breeze `172151e3` | Same |
| `shipping-zh` | Full Whisper `49e6aa28` | Mandarin forced, on the six English inputs only |

All arms use the pinned MLX runners, word timestamps on, previous-text conditioning off and stock decoding. English WER and Mandarin CER are reported separately with `score_transcripts.py`. Full Whisper, Turbo and Breeze repeat on one short clean case and on silence to check text repeatability. Timed invocations don't cache a model.

### Changes to the plan

The criteria were fixed before the runs they govern. Their wording was later edited to read against `main`; no threshold or rule changed.

On 2026-11-03, after the runs, this summary was split out of one write-up covering every question, so that each question has its own summary and decision. No result changed. Nothing was rerun for the split.

## Results

The 17 audio files span 33.76 minutes. Two WAVs are byte-identical to the trial's (stocktake and digital silence); five of its conditions now have different waveforms. Fourteen independent source calls contribute to language scores. The stressed handoff and logistics mixes repeat source text and are excluded. Each rate is total edits divided by total language-specific reference units.

| Word-timestamp recognizer | English WER (6 calls; 3,028 words) | Mandarin CER (8 calls; 3,095 characters) |
| --- | ---: | ---: |
| Full Whisper, Mandarin forced everywhere | 84.41% (2,556) | 9.98% (309) |
| Full Whisper, declared language | 2.18% (66) | 9.98% (309) |
| Turbo Q4, declared language | **1.98% (60)** | **7.59% (235)** |
| Breeze, declared language | 7.43% (225) | 12.08% (374) |
| [Full Whisper component baseline](../../experiments/synthetic-call/reference/transcript-baseline.json), no word timestamps | 1.88% (57) | 9.27% (287) |

- **Language:** declaring English improved every English call.
- **Turbo:** the trial's "Turbo never loses" result **does not hold**. Full Whisper made fewer edits on four Mandarin scripts (planning, scheduling, design, localization) and two English scripts (design, tabletop). Turbo's 74-edit Mandarin advantage includes 66 edits from onboarding.
- **Breeze:** it had the highest error rate of the three recognizers in both languages.
- **Baseline:** no recognizer with word timestamps beat the baseline, which has none, in both languages. The baseline also uses different decoder settings, so we can't say word timestamps caused the gap.

**Replication of the trial.** On the stocktake WAV shared with the trial, its 48/48/17 errors for full/Turbo/Breeze repeated. On the resynthesized logistics pair all three worsened with overlap (28→35, 20→34, 17→31 edits). Compared with the clean handoff, the version with one speaker quieter and noise added went from 32 to 13 edits for full Whisper, 13 to 16 for Turbo, and 11 to 11 for Breeze. The trial found that Breeze improved on this kind of audio, but here it didn't change.

**Repeatability.** Each model ran twice on the handoff and silence recordings. Both runs gave the same text once normalized.

**Limits.** Generated scripts are intended speech, and TTS pronunciation can contribute to text errors. These results don't extend to real rooms, longer meetings or listener-confirmed transcripts.

## Runtime and memory

One inference process ran at a time on the M2 Pro with 16 GB. Timings include process startup, model load and device teardown, measured with `/usr/bin/time -l`. The desktop was in normal use, a two-job Swift compilation overlapped part of the early English audit and silence timing, and toolchain caches were warm. These are individual observations on this machine, not latency guarantees.

| ASR, script-matched language | Median wall time, 17 fixtures | Total stage time | Peak process footprint | Fastest on |
| --- | ---: | ---: | ---: | --- |
| Full Whisper | 15.84 s | 344.99 s | 9.00 GB | 0 |
| Turbo Q4 | 7.86 s | 181.81 s | 4.14 GB | All 16 speech recordings |
| Breeze | 30.59 s | 640.58 s | 12.92 GB | Digital silence |

## Decision

Specify the spoken language, with Mandarin as the default. Keep full Whisper as the default recognizer until the private listening review, and offer Turbo for turnaround. See decision 12.

## Open questions

Accuracy against a listener-confirmed reference, real-room noise and long meetings remain open. The next step is the private listening review, before any change to the default.

## Where this ran

- **Code:** the collection is the one merged in #32 (`4c8c2f0`). The runs used development commits based on it, before the pipeline options merged: `--language` (#33) and `--asr turbo-q4` (#34). The development commits are not on `main`.
- **Models and weights:** the revisions in the plan, and in [`pins.py`](../../experiments/pipelines/whisper-sortformer/pins.py).
- **Machine:** one M2 Pro with 16 GB, one inference process at a time.
- **Kept outside the repository:** raw calls and predictions, under benchmark ID `expanded-pipeline-20261102`. Public results contain counts and digests only.
