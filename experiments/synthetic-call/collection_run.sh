#!/bin/bash
# Run the whole 17-recording comparison up to the hand grading, one model at a time.
# Usage: collection_run.sh FIXTURES RESULTS [--plan | --step NAME]
set -eu
usage="usage: collection_run.sh FIXTURES RESULTS [--plan | --step NAME]"
[[ $# -ge 2 ]] || { echo "$usage" >&2; exit 2; }
fixtures=$1
results=$2
mode=${3:-}
step=${4:-}
case "$mode" in
    "" | --plan) [[ $# -le 3 ]] || { echo "$usage" >&2; exit 2; };;
    --step) [[ $# -eq 4 ]] || { echo "$usage" >&2; exit 2; };;
    *) echo "$usage" >&2; exit 2;;
esac
steps="decode recaps diarize split turns replays scores"
cases="onboarding english-audit silence handoff stocktake localization scheduling design logistics english-handoff english-design english-training english-tabletop english-committee handoff-channel logistics-overlap script"
root=$(cd "$(dirname "$0")/../.." && pwd)
synth="$root/experiments/synthetic-call"
pipe="$root/experiments/pipelines/whisper-sortformer"
python="$synth/.venv/bin/python"
pipe_python="$pipe/.venv/bin/python"

if [[ "$mode" = --plan ]]; then
    printf '%s\n' $steps
    exit 0
fi
case "$results" in /*) ;; *) echo "RESULTS must be an absolute path" >&2; exit 2;; esac
[[ -d "$fixtures" ]] || { echo "no fixtures folder: $fixtures" >&2; exit 2; }
fixtures=$(cd "$fixtures" && pwd)
if [[ "$mode" = --step ]]; then
    case " $steps " in *" $step "*) ;; *) echo "unknown step: $step (one of: $steps)" >&2; exit 2;; esac
    if [[ "$step" = decode ]]; then
        [[ ! -e "$results" ]] || { echo "--step decode creates RESULTS; choose a new folder" >&2; exit 2; }
    else
        [[ -d "$results" ]] || { echo "no RESULTS folder: $results; run the decode step first" >&2; exit 2; }
    fi
elif [[ -e "$results" ]]; then
    echo "RESULTS already exists; choose a new folder, or rerun one failed step with --step" >&2
    exit 2
fi
for needed in "$python" "$pipe_python" "$root/experiments/mlx/.venv/bin/python" "$pipe/.build/release/fluidaudiocli" \
    "$pipe/.build/release/who-diarize" "$root/experiments/diarization/.build/release/diarexp"; do
    [[ -e "$needed" ]] || { echo "missing $needed; run experiments/synthetic-call/collection_setup.sh first" >&2; exit 2; }
done

need() {  # need STEP FROM CASE FILE...: stop before running STEP if an earlier step's output is missing
    local step=$1 from=$2 case=$3 file
    shift 3
    for file in "$@"; do
        [[ -e "$results/$case/$file" ]] || {
            echo "step $step needs $case/$file, written by the $from step; run the steps in order ($steps)" >&2
            exit 2
        }
    done
}

check_inputs() {
    local step=$1 case
    case "$step" in
        recaps) for case in onboarding english-audit silence; do need recaps decode $case input.sha256; done;;
        diarize | split) for case in $cases; do need $step decode $case input.sha256 audio.wav; done;;
        turns)
            for case in $cases; do
                [[ $case = silence ]] && continue
                need turns decode $case input.sha256 whisper.json breeze.json
                need turns diarize $case who.json sortformer.json weights.json
            done;;
        replays)
            for case in onboarding english-audit; do
                need replays recaps $case fast/asr.json fast/diarization.json fast/audio.wav fast/speakers.json
            done
            need replays decode english-training turbo.json audio.wav
            need replays diarize english-training who.json;;
        scores)
            for case in $cases; do
                need scores decode $case input.sha256 audio.wav whisper.json turbo.json breeze.json
                need scores diarize $case who.json sortformer.json
                need scores split $case split/spans.json
                [[ $case = silence ]] || need scores turns $case turn-order.json
            done
            need scores diarize onboarding weights.json
            for case in onboarding english-audit; do
                for arm in pipeline exact fast; do need scores recaps $case $arm/summary.json; done
            done
            need scores recaps silence pipeline/summary.json;;
    esac
}

lines() {  # lines CASE ASR DIARIZATION AUDIO OUT [compare_lines options]
    local case=$1 asr=$2 diarization=$3 audio=$4 out=$5
    shift 5
    "$pipe_python" "$pipe/compare_lines.py" "$results/$case/$asr" "$results/$case/$diarization" "$results/$case/$audio" \
        "$results/$case/$out" "$@"
}

replays() {
    export HF_HUB_OFFLINE=1
    "$pipe_python" "$pipe/recap.py" run "$fixtures/onboarding/call.wav" "$results/onboarding/pause-pipeline" \
        --diarizer who --split-digital-pauses --no-summary
    "$pipe_python" "$pipe/recap.py" run "$fixtures/english-audit/call.wav" "$results/english-audit/segment-pipeline" \
        --asr turbo-q4 --diarizer who --language en --keep-asr-segments --no-summary
    for case in english-audit onboarding; do
        lines "$case" fast/asr.json fast/diarization.json fast/audio.wav segment-lines \
            --keep-segments --speakers "$results/$case/fast/speakers.json"
    done
    lines english-training turbo.json who.json audio.wav original-lines
    lines english-training turbo.json who.json audio.wav segment-lines \
        --keep-segments --speakers "$results/english-training/original-lines/speakers.json"
}

run_step() {
    check_inputs "$1"
    echo "== $1"
    case "$1" in
        decode) "$synth/collection_decode.sh" "$fixtures" "$results";;
        recaps | diarize | split | turns) "$python" "$synth/collection_followup.py" "$fixtures" "$results" "$1";;
        replays) replays;;
        scores) "$python" "$synth/collection_scores.py" "$fixtures" "$results" > "$results/scores.json";;
    esac
}

if [[ "$mode" = --step ]]; then
    run_step "$step"
    exit 0
fi
for name in $steps; do
    run_step "$name"
done
cat <<DONE
Measurements are in $results/scores.json. Timings will differ from the committed results.
Hand step left: grade the recaps against the fixed checks in the experiment summary. New text can't inherit an earlier judgment.
DONE
