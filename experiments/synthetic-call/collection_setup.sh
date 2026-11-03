#!/bin/bash
# Prepare everything collection_run.sh needs: environments, Swift binaries, pinned models and frozen code. Needs the network.
set -eu
root=$(git rev-parse --show-toplevel)
cd "$root"
synth=experiments/synthetic-call
pipe=experiments/pipelines/whisper-sortformer
mlx=experiments/mlx
uv sync --locked --project "$synth"
uv sync --locked --project "$pipe"
uv sync --locked --project "$mlx"
swift build -c release --package-path "$pipe" --product fluidaudiocli
swift build -c release --package-path "$pipe" --product who-diarize
swift build -c release --package-path experiments/diarization --product diarexp
uv run --project "$pipe" "$pipe/recap.py" setup --asr all --who
uv run --project "$mlx" python -c 'from huggingface_hub import snapshot_download as s; print(s(repo_id="eoleedi/Breeze-ASR-25-mlx", revision="172151e3fd93ab6dc841d639f23dd48b24bc8301"))'
uv run --project "$synth" "$synth/collection_weights.py" setup
# The action comparison runs its frozen prompts from this commit, which is not on main.
history=c714e0535411e04ec291172e0a7e70c44443df15
git cat-file -e "$history^{commit}" 2>/dev/null || git fetch origin "$history"
echo "setup complete; next: $synth/collection_run.sh FIXTURES RESULTS"
