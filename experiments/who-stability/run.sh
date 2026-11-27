#!/bin/bash
# Run Who on growing prefixes of the synthetic calls and measure live-label stability. No hand step.
# Usage: run.sh FIXTURES RESULTS
#   FIXTURES  the verified 17-recording synthetic collection (experiments/synthetic-call/collection.py)
#   RESULTS   a new folder; gets prefixes.json (Who's labels), time.txt (peak memory) and stability.json
set -eu
[[ $# -eq 2 ]] || { echo "usage: run.sh FIXTURES RESULTS" >&2; exit 2; }
root=$(cd "$(dirname "$0")/../.." && pwd)
here="$root/experiments/who-stability"
synth="$root/experiments/synthetic-call"
python="$synth/.venv/bin/python"
binary="$here/.build/release/who-prefixes"
models=${WHO_MODELS:-"$HOME/Library/Application Support/meeting-recap/who"}
fixtures=$(cd "$1" && pwd)
results=$2
[[ ! -e "$results" ]] || { echo "RESULTS already exists; choose a new folder" >&2; exit 2; }
for needed in "$python" "$binary"; do
    [[ -e "$needed" ]] || { echo "missing $needed; run experiments/who-stability/setup.sh first" >&2; exit 2; }
done
cases="script handoff logistics stocktake scheduling design onboarding localization english-audit english-handoff english-design english-tabletop english-committee english-training handoff-channel logistics-overlap"
(cd "$synth" && "$python" collection.py "$fixtures" --check)
mkdir -p "$results"
args=()
for case in $cases; do args+=("$case=$fixtures/$case/call.wav"); done
/usr/bin/time -l "$binary" "$models" "$results/prefixes.json" 15 "${args[@]}" 2> "$results/time.txt"
"$python" "$here/stability.py" "$fixtures" "$results/prefixes.json" > "$results/stability.json"
echo "Measurements are in $results/stability.json; peak memory is in $results/time.txt."
