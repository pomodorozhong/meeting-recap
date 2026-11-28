#!/bin/bash
# Prepare everything run.sh needs: the environment and the five pinned models. Needs the network.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
uv sync --locked --project "$here"
uv run --project "$here" "$here/models.py" download
echo "setup complete; next: $here/run.sh FIXTURES OUT"
