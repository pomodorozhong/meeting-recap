# oMLX check

Checks whether [oMLX](https://github.com/jundot/omlx) 0.8.4 can run the recap stage with the same output as `summary_stage.py`, for #60. The plan, how to run it and the results are in [the experiment summary](../../docs/experiments/2026-11-28-omlx-check.md).

- `setup.sh` syncs this folder's environment (oMLX from its pinned release wheel, with oMLX's own MLX and mlx-lm pins) and the pipeline's, and checks the pinned model and oMLX's native kernels (needs the network).
- `run.sh FIXTURES OUT` runs, for each of four synthetic calls: the pipeline's `summary_stage.py` unchanged, `control.py` (the same calls in oMLX's environment), and a fresh `omlx serve` that `client.py` sends the prompt to twice. Then `compare.py` writes `OUT/results.json`.
- `common.py` holds a copy of the pipeline's prompt and transcript-line code; `tests/experiments/test_omlx_check.py` checks the copy still matches.
