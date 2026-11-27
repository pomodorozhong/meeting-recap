# Small recap models

Recaps of the synthetic collection's exact turns from Gemma4 E2B, MiniCPM5 2B, LFM3-1.7B and Spark X2.6-4B, next to the Qwen3.5 9B baseline, with the pipeline's prompt. The plan, how to run it and the results are in [the experiment summary](../../docs/experiments/2026-11-28-small-recap-models.md).

- `setup.sh` syncs the environment and downloads the pinned models (needs the network).
- `run.sh FIXTURES OUT [MODEL ...]` runs each model in its own process, then writes `OUT/scores.json`.
- `run.py` holds the model pins and a copy of the pipeline's prompt; `tests/experiments/test_small_recap_models.py` checks the copy still matches.
- `scores.py OUT` collects measurements and grades into counts and digests that can be committed.
