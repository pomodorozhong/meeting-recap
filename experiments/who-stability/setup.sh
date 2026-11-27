#!/bin/bash
# Prepare what run.sh needs: the synthetic-call environment, the who-prefixes binary and Who's pinned
# int8 weights. Needs the network.
set -eu
root=$(git rev-parse --show-toplevel)
cd "$root"
uv sync --locked --project experiments/synthetic-call
uv sync --locked --project experiments/pipelines/whisper-sortformer
swift build -c release --package-path experiments/who-stability --product who-prefixes
uv run --project experiments/pipelines/whisper-sortformer experiments/pipelines/whisper-sortformer/recap.py setup --who
echo "setup complete; next: experiments/who-stability/run.sh FIXTURES RESULTS"
