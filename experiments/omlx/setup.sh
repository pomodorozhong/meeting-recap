#!/bin/bash
# Prepare everything run.sh needs: oMLX's environment, the pipeline's environment, and the pinned model.
# Needs the network.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
uv sync --locked --project "$here"
uv sync --locked --project "$root/experiments/pipelines/whisper-sortformer"
"$here/.venv/bin/python" -c 'import sys; sys.path.insert(0, sys.argv[1]); import control; print(control.snapshot())' "$here"
"$here/.venv/bin/python" -c 'from omlx.custom_kernels import native_kernel_status as s; print(s())'
echo "setup complete; next: $here/run.sh FIXTURES OUT"
