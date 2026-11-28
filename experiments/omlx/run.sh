#!/bin/bash
# Recap four synthetic calls with the stage's summary_stage.py, with the same code in oMLX's environment, and
# through an oMLX server, one process at a time, then compare. Run setup.sh first.
#
#   experiments/omlx/run.sh FIXTURES OUT
#
# FIXTURES is the verified 17-recording collection; OUT is a new folder outside Git.
set -eu
if [ $# -ne 2 ]; then echo "usage: $0 FIXTURES OUT" >&2; exit 2; fi
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
pipe="$root/experiments/pipelines/whisper-sortformer"
fixtures=$1 out=$2
case "$out" in "$root"*) echo "OUT must be outside the repository" >&2; exit 1;; esac
python="$here/.venv/bin/python"
pipe_python="$pipe/.venv/bin/python"
port=8771
[ -x "$python" ] && [ -x "$pipe_python" ] || { echo "run $here/setup.sh first" >&2; exit 1; }
export HF_HUB_OFFLINE=1  # setup.sh downloaded the model; nothing may download now
mkdir -p "$out"
"$python" "$here/lines.py" "$fixtures" "$out"
snapshot=$("$python" -c 'import sys; sys.path.insert(0, sys.argv[1]); import control; print(control.snapshot())' "$here")
calls=$("$python" -c 'import sys; sys.path.insert(0, sys.argv[1]); import common; print(" ".join(common.CALLS))' "$here")

for call in $calls; do
    dir="$out/$call"
    /usr/bin/time -l "$pipe_python" "$pipe/summary_stage.py" "$dir/lines.json" "$dir/stage.json" 2> "$dir/stage.time" < /dev/null
    /usr/bin/time -l "$python" "$here/control.py" "$dir/lines.json" "$dir/control.json" 2> "$dir/control.time" < /dev/null

    # A fresh server per call, so its peak footprint belongs to that call. Its data and SSD cache stay in OUT.
    # The memory guard is off: with the desktop in normal use it refuses to load the 5.8 GB model, which the
    # stage loads without a guard.
    models="$dir/omlx-models" home="$dir/omlx-home"
    mkdir -p "$models" "$home"
    ln -sfn "$snapshot" "$models/qwen3.5-9b"
    # oMLX detects Qwen3.5 as a vision-language model and would run it through its mlx-vlm fork; the stage runs
    # it as text through mlx-lm, so the check pins the text path.
    printf '{"version": 3, "models": {"qwen3.5-9b": {"model_type_override": "llm"}}}\n' > "$home/model_settings.json"
    /usr/bin/time -l "$here/.venv/bin/omlx" serve --model-dir "$models" --base-path "$home" --port "$port" \
        --headless --no-hf-cache --memory-guard off --paged-ssd-cache-dir "$home/ssd-cache" --log-level warning \
        > "$dir/omlx-server.log" 2> "$dir/omlx.time" < /dev/null &
    server=$!
    for _ in $(seq 120); do curl -sf "http://127.0.0.1:$port/health" > /dev/null && break; sleep 1; done
    curl -sf "http://127.0.0.1:$port/v1/models" > "$dir/omlx-models.json"
    "$python" "$here/client.py" "$dir/lines.json" "$dir/omlx.json" --port "$port"
    pkill -INT -P "$server" || true; wait "$server" || true
done
"$python" "$here/compare.py" "$out" > "$out/results.json"
echo "wrote $out/results.json"
