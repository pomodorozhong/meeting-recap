#!/bin/bash
# Recap the exact turns of the collection's onboarding and English audit calls with each model, one model per
# process, then collect the measurements. Run setup.sh first.
#
#   experiments/small-recap-models/run.sh FIXTURES OUT [--thinking-off|--thinking|--thinking-budget|--thinking-sampled] [MODEL ...]
#
# FIXTURES is the verified 17-recording collection; OUT is a new folder outside Git. With no arm flag, every arm
# runs in turn: thinking off into OUT/<call>/<model>, --thinking into <model>-thinking, then the later thinking
# variants --thinking-budget and --thinking-sampled into <model>-thinking-budget and <model>-thinking-sampled. An
# arm flag runs that arm alone. With no MODEL, every model in run.py runs (only the four that never finished with
# greedy thinking for the later variants). A run that already finished a case is skipped, and a process with
# nothing to do leaves the earlier OUT/<run>.time in place.
set -eu
usage="usage: $0 FIXTURES OUT [--thinking-off|--thinking|--thinking-budget|--thinking-sampled] [MODEL ...]"
if [ $# -lt 2 ]; then echo "$usage" >&2; exit 2; fi
here=$(cd "$(dirname "$0")" && pwd)
fixtures=$1 out=$2
shift 2
arms="" models=""
for arg in "$@"; do
    case "$arg" in
        --thinking-off|--thinking|--thinking-budget|--thinking-sampled)
            [ -z "$arms" ] || { echo "give at most one arm flag; $usage" >&2; exit 2; }
            arms=$arg ;;
        --*) echo "unknown option $arg; $usage" >&2; exit 2 ;;
        *) models="$models $arg" ;;
    esac
done
arms=${arms:---thinking-off --thinking --thinking-budget --thinking-sampled}
python="$here/.venv/bin/python"
[ -x "$python" ] || { echo "run $here/setup.sh first" >&2; exit 1; }
known=" $("$python" "$here/models.py" list) "
for model in $models; do
    case "$known" in *" $model "*) ;; *) echo "unknown model $model; models:$known" >&2; exit 2 ;; esac
done
mkdir -p "$out"
export HF_HUB_OFFLINE=1  # every model was downloaded by setup.sh; a missing one fails instead of downloading
for arm in $arms; do
    case "$arm" in
        --thinking-off) flag="" suffix="" listing=list ;;
        --thinking) flag=$arm suffix=-thinking listing=list ;;
        *) flag=$arm suffix=-${arm#--} listing=list-rerun ;;
    esac
    allowed=" $("$python" "$here/models.py" $listing) "
    for model in ${models:-$allowed}; do
        case "$allowed" in
            *" $model "*) ;;
            *) echo "$model$suffix: not part of this arm, skipping"; continue ;;
        esac
        todo=$("$python" "$here/run.py" "$fixtures" "$out" --model "$model" $flag --todo)
        if [ -z "$todo" ]; then
            echo "$model$suffix: already done, skipping"
            continue
        fi
        # time writes to its own file, so run.py's errors stay on the terminal.
        /usr/bin/time -l -o "$out/$model$suffix.time" "$python" "$here/run.py" "$fixtures" "$out" --model "$model" $flag \
            < /dev/null
        grep -E "real|peak memory footprint" "$out/$model$suffix.time" || true
    done
done
"$python" "$here/scores.py" "$out" > "$out/scores.json"
echo "wrote $out/scores.json"
echo "Hand step left: grade each recap against the fixed checks in docs/experiments/2026-11-28-small-recap-models.md,"
echo "save the verdicts as $out/judgments.json, and rerun scores.py to add them."
