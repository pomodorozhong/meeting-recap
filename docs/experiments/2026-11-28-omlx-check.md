# 2026-11-28: oMLX against mlx-lm for the recap stage

**Status:** complete

**Outcome:** oMLX 0.8.4 did not reproduce the stage's output: its reply matched `summary_stage.py` byte for byte on 1 of 4 synthetic calls. The same code in oMLX's newer MLX and mlx-lm matched on all 4, so the server causes the difference, not the versions. It loaded the pinned snapshot, its memory peak matched the stage's within 0.1 GB, and it took thinking off. A repeat run reused the cached prompt and finished 18 to 36% faster, from skipping the model load and the prefill; generation was no faster. Under the rule set before the run, the slow runs in the recap-stage plan keep `mlx-lm`.

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/omlx/setup.sh` |
| Run everything | `experiments/omlx/run.sh "$FIXTURES" "$OUT"` |
| Check saved results without models | `uv run --project experiments/omlx experiments/omlx/compare.py "$OUT"` rebuilds the comparison from saved replies |

- **It needs:** `FIXTURES`, the verified 17-recording collection built by [`collection.py`](../../experiments/synthetic-call/README.md#seventeen-recording-collection), and `OUT`, a new absolute path outside Git. Port 8771 free on the loopback interface.
- **It writes:** under `OUT`, the transcript lines of each call, every reply from the three runners below with its timing, the `/usr/bin/time -l` report of each runner's process, and the comparison in `OUT/results.json`.
- **Takes about:** 17 minutes for the four calls and three runners (`run.sh` on 2026-11-28, model already downloaded).
- **By hand:** nothing.
- **Expect to differ:** timings and memory on any rerun.

## Question

Can [oMLX](https://github.com/jundot/omlx) run the recap stage with the same output as `summary_stage.py` today, and is it faster on a repeat run? This is #60.

- **Decision it informs:** whether the slow runs in the [recap-stage plan](2026-11-04-recap-stage-real-calls.md) use oMLX. If any of the first four checks fails, they keep running `mlx-lm` as now, and nothing changes.
- **Expected result:** oMLX pins its own MLX and mlx-lm, so its replies may differ from the stage's by a few tokens. Its prefix cache should make a repeat run of the same prompt faster.
- **Builds on:** decision 7 (the recap model and MLX only) and #60's five checks.

## Plan

- **Input:** the script's exact turns of four synthetic calls from the collection, built as the 2026-11-02 recap experiment's `exact` arm built them: onboarding (1.7 min), English audit (3.2 min), English training (3.4 min) and `script` (5.1 min, the longest call in the collection). Each fits in one prompt, so no merge step runs.
- **Assumptions:** one M2 Pro with 16 GB, one runner process at a time, model already downloaded.

| Run ID | Runner | Versions | Settings |
| --- | --- | --- | --- |
| `stage` | The pipeline's own `summary_stage.py`, unchanged | MLX 0.32.4, mlx-lm 0.32.2 (the pipeline's lock) | `mlx-community/Qwen3.5-9B-4bit` at `8b2b98c0`; the pipeline's prompt, greedy, thinking off, 4,096-token cap |
| `control` | The same calls as `summary_stage.py`, in oMLX's environment | MLX 0.32.5, mlx-lm at `0d4d3d04` (oMLX 0.8.4's pins) | Same |
| `omlx` | `omlx serve` 0.8.4 from the release wheel (sha256 `0f1e350d…`), headless on 127.0.0.1, then its OpenAI-compatible chat endpoint | oMLX's pins, native kernels loaded | Same model folder, through a model directory that links to the pinned snapshot. `model_type_override: "llm"` and `--memory-guard off` (see below); speculative decoding and KV-cache compression stay at their default, off. Each request sets temperature 0, top-p 1, top-k 0, min-p 0, no repetition or presence penalty, `chat_template_kwargs` `enable_thinking: false`, 4,096 max tokens. oMLX's own data and SSD cache live under `OUT`. Every call is sent twice in a row; the second is the repeat run |

Two oMLX defaults were found in a smoke test with a one-line prompt, before any run on the experiment's input, and are overridden so that oMLX runs the model the way the stage does:

- oMLX detects Qwen3.5 as a vision-language model, because its snapshot has image and video processor files, and would run it through its own mlx-vlm fork. The stage loads it as text through mlx-lm. The check sets `model_type_override: "llm"` for the model.
- oMLX's memory guard (default tier "balanced") refused to load the 5.8 GB model, allowing only 3.7 GB with the desktop in normal use. The stage has no such guard. The check turns it off.

`control` separates the two possible causes of a difference: if `control` matches `omlx` but not `stage`, the newer MLX and mlx-lm cause it, not the server.

**The five checks of #60**, decided before the run:

1. **Same output:** for each call, the `omlx` reply matches the `stage` reply byte for byte. Passes only if all four first-run replies match. Any difference is reported with the first differing character and whether `control` shares it.
2. **Pinned revision:** oMLX loads the pinned snapshot folder, and the reply shows it used that model. Passes if the server lists the model from the linked folder and no download happens (`HF_HUB_OFFLINE=1`, `--no-hf-cache`).
3. **Memory:** a peak figure comparable with the stage's. The stage's process peak footprint and oMLX's server process peak footprint are both read from `/usr/bin/time -l`. Passes if oMLX's peak can be read per run this way.
4. **Thinking switch and template:** passes if every reply has no thinking text and the server accepted `enable_thinking: false`.
5. **Speed:** wall time per call, first and repeat run, against `stage`, with the prompt tokens oMLX reports as cached. Reported, not passed or failed.

### Changes to the plan

None.

## Results

| Check | Result |
| --- | --- |
| 1. Same output | **Fails.** oMLX matched the stage on onboarding only. On English audit, English training and `script`, its reply first differs at character 217, 492 and 356. `control` matched the stage on all four calls |
| 2. Pinned revision | Passes. The server listed only `qwen3.5-9b` from the linked snapshot folder, with downloads turned off |
| 3. Memory | Passes. The server's peak footprint can be read per call from `/usr/bin/time -l`, and it was within 0.1 GB of the stage's on every call (6.9 to 7.6 GB) |
| 4. Thinking switch | Passes. oMLX accepted `enable_thinking: false` per request, and no reply had thinking text |

- **Where the difference comes from.** `control` runs the stage's code with oMLX's pins (MLX 0.32.5, mlx-lm at `0d4d3d04`) and reproduced the stage's replies exactly, so the version change alone doesn't explain the difference. oMLX's own serving path does: it generates through mlx-lm's batch generator with its paged cache and native kernels, which can change the low-order bits of the computation enough to flip a greedy choice. This run didn't isolate which of those does it.
- **oMLX is repeatable with itself.** Each call's repeat run gave the same reply as its first run, byte for byte. Its replies are deterministic, just not the stage's.
- **Same prompt.** oMLX counted the same prompt tokens as the stage on every call (832, 942, 1,275 and 2,307), so its chat template rendered the prompt the same way.
- **The differing replies weren't graded.** The plan only asks whether the bytes match. Whether oMLX's recaps are better or worse is a separate question.

| Call | Stage recap, s | oMLX first run, s | oMLX repeat, s | oMLX time to first token, first / repeat | Prompt tokens cached on repeat |
| --- | ---: | ---: | ---: | ---: | ---: |
| Onboarding | 19.5 | 22.4 | 14.4 | 4.5 / 0.18 s | 825 of 832 |
| English audit | 43.4 | 51.7 | 42.6 | 5.1 / 0.17 s | 935 of 942 |
| English training | 34.5 | 37.2 | 26.8 | 6.7 / 0.18 s | 1,268 of 1,275 |
| `script` | 90.4 | 85.6 | 69.9 | 12.0 / 0.29 s | 2,300 of 2,307 |

oMLX's first-run times include about 3.9 s of model loading on the first request; the stage's recap times don't include loading. Where oMLX's reply had a different length from the stage's, the times compare different amounts of generated text (on English audit oMLX wrote 3,108 characters against the stage's 2,794). The repeat run gained 8 to 16 s: the 3.9 s of loading that only the first request pays, plus 4 to 12 s of prefill that the prefix cache skipped. Generation, which takes most of the time, was no faster. On long calls the prefill is a bigger share, so a repeat would gain more there, but this run didn't measure that.

**Limits.** Four synthetic calls of at most 5.1 minutes, all in one prompt, one run each. #60 asks for the longest available transcript; the long real calls stay in the private dataset and aren't part of this run, so the speed figures say little about two-hour calls.

## Runtime and memory

| Call | Stage process: wall / peak footprint | Control process | oMLX server process, both requests |
| --- | ---: | ---: | ---: |
| Onboarding | 38 s / 6.94 GB | 23 s / 6.81 GB | 44 s / 6.90 GB |
| English audit | 50 s / 6.96 GB | 48 s / 6.83 GB | 102 s / 6.94 GB |
| English training | 41 s / 7.11 GB | 39 s / 6.98 GB | 72 s / 7.06 GB |
| `script` | 97 s / 7.56 GB | 95 s / 7.42 GB | 163 s / 7.57 GB |

All from `/usr/bin/time -l`, one process at a time on the M2 Pro with the desktop in normal use. The oMLX column covers a server's whole life for one call: start-up, two requests and shutdown. The stage and control MLX peaks were the same to the byte on every call (6.21 to 6.71 GB); oMLX doesn't report an MLX peak.

## Decision

Keep running the recap stage, and the slow runs of the recap-stage plan, with `mlx-lm` in its own process, as now. oMLX fails the first check: its replies aren't the stage's, so it would break the plan's exact-repeat control and make its results incomparable with earlier ones. Its prefix cache does work, but it saves only the prefill, which is a small share of a recap's time on these calls. See decision 21.

## Open questions

- Which part of oMLX's serving path changes the output: the batch generator, the paged cache or the native kernels? oMLX may have settings that turn some of them off; this run didn't try.
- If the project ever runs many recaps of one long transcript (Stage A's variants share the transcript, not the prompt), would oMLX's cache save enough to accept non-identical output? That needs a long-call measurement and the project owner's decision.

## Where this ran

- **Code:** commit `8d9cdf3` on the branch for #60, which holds the plan and every script the run used.
- **Models and weights:** the revisions in the plan.
- **Machine:** one M2 Pro with 16 GB, macOS 26.6.2. Stage: MLX 0.32.4, mlx-lm 0.32.2. Control and oMLX: oMLX 0.8.4 (release wheel sha256 `0f1e350de597ce0d9948003d95cd3cec1f3bc38e85c6ec7b9991ca4b51b96ae6`), MLX 0.32.5, mlx-lm at `0d4d3d04`, transformers 5.22.2, all native kernels loaded.
- **Kept outside the repository:** the transcript lines and replies, in the private review dataset under benchmark ID `omlx-check-20261128`. [The saved comparison](2026-11-28-omlx-check-results.json) holds digests, counts and times only.
