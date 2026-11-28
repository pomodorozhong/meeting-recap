# 2026-11-28: oMLX against mlx-lm for the recap stage

**Status:** planned

**Outcome:** pending.

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/omlx/setup.sh` |
| Run everything | `experiments/omlx/run.sh "$FIXTURES" "$OUT"` |
| Check saved results without models | `uv run --project experiments/omlx experiments/omlx/compare.py "$OUT"` rebuilds the comparison from saved replies |

- **It needs:** `FIXTURES`, the verified 17-recording collection built by [`collection.py`](../../experiments/synthetic-call/README.md#seventeen-recording-collection), and `OUT`, a new absolute path outside Git. Port 8771 free on the loopback interface.
- **It writes:** under `OUT`, the transcript lines of each call, every reply from the three runners below with its timing, the `/usr/bin/time -l` report of each runner's process, and the comparison in `OUT/results.json`.
- **Takes about:** pending.
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

Pending.

**Limits.** Synthetic calls of at most 5.1 minutes, all in one prompt. #60 asks for the longest available transcript; the long real calls stay in the private dataset and aren't part of this run, so the speed figures say little about two-hour calls.

## Runtime and memory

Pending.

## Decision

Pending.

## Open questions

## Where this ran

- **Code:** pending.
- **Models and weights:** the revisions in the plan.
- **Machine:** one M2 Pro with 16 GB.
- **Kept outside the repository:** the transcript lines and replies, under `OUT`. Public results hold digests, counts and times only.
