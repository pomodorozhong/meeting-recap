#!/bin/bash
# Recap the exact turns of the collection's onboarding and English audit calls with each model, one model per
# process, then collect the measurements. Run setup.sh first.
#
#   experiments/small-recap-models/run.sh FIXTURES OUT [--thinking|--thinking-budget|--thinking-sampled] [MODEL ...]
#
# FIXTURES is the verified 17-recording collection; OUT is a new folder outside Git. With no MODEL, every model
# in run.py runs. --thinking runs the thinking-on arm instead, into OUT/<call>/<model>-thinking;
# --thinking-budget and --thinking-sampled run the later thinking variants, into <model>-thinking-budget and
# <model>-thinking-sampled. A run that already finished a case is skipped.
set -eu
if [ $# -lt 2 ]; then echo "usage: $0 FIXTURES OUT [--thinking|--thinking-budget|--thinking-sampled] [MODEL ...]" >&2; exit 2; fi
here=$(cd "$(dirname "$0")" && pwd)
fixtures=$1 out=$2
shift 2
thinking="" suffix=""
case "${1:-}" in
    --thinking) thinking=$1 suffix=-thinking; shift ;;
    --thinking-budget) thinking=$1 suffix=-thinking-budget; shift ;;
    --thinking-sampled) thinking=$1 suffix=-thinking-sampled; shift ;;
esac
python="$here/.venv/bin/python"
[ -x "$python" ] || { echo "run $here/setup.sh first" >&2; exit 1; }
listing=list
case "$suffix" in -thinking-budget|-thinking-sampled) listing=list-rerun ;; esac
models=${*:-$("$python" "$here/models.py" $listing)}
mkdir -p "$out"
export HF_HUB_OFFLINE=1  # every model was downloaded by setup.sh; a missing one fails instead of downloading
for model in $models; do
    /usr/bin/time -l "$python" "$here/run.py" "$fixtures" "$out" --model "$model" $thinking \
        2> "$out/$model$suffix.time" < /dev/null
    tail -n 25 "$out/$model$suffix.time" | grep -E "real|peak memory footprint" || true
done
"$python" "$here/scores.py" "$out" > "$out/scores.json"
echo "wrote $out/scores.json"
echo "Hand step left: grade each recap against the fixed checks in docs/experiments/2026-11-28-small-recap-models.md,"
echo "save the verdicts as $out/judgments.json, and rerun scores.py to add them."
