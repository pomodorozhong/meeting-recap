#!/bin/bash
# Recreate the serial word-timestamp ASR matrix; inputs verified before inference.
set -eu
fixtures=$(cd "$1" && pwd)
out=$2
case "$out" in /*) ;; *) echo "use an absolute external results folder" >&2; exit 2;; esac
if git -C "$(dirname "$out")" rev-parse --git-dir >/dev/null 2>&1; then exit 2; fi
root=$(git rev-parse --show-toplevel)
synth="$root/experiments/synthetic-call"
mlx="$root/experiments/mlx"
export HF_HUB_OFFLINE=1
"$synth/.venv/bin/python" "$synth/collection.py" --check "$fixtures"
mkdir "$out"
for id in onboarding english-audit silence handoff stocktake localization scheduling design logistics english-handoff english-design english-training english-tabletop english-committee handoff-channel logistics-overlap script; do
    lang=zh
    case "$id" in english-*) lang=en;; esac
    mkdir "$out/$id"
    ffmpeg -nostdin -loglevel error -i "$fixtures/$id/call.wav" -ac 1 -ar 16000 -c:a pcm_f32le "$out/$id/audio.wav"
    shasum -a 256 "$fixtures/$id/call.wav" | cut -d' ' -f1 > "$out/$id/input.sha256"
    models="whisper turbo breeze"
    if [[ "$lang" = en ]]; then models="$models shipping-zh"; fi
    if [[ "$id" = handoff || "$id" = silence ]]; then models="$models whisper-repeat turbo-repeat breeze-repeat"; fi
    for model in $models; do
        language=$lang
        case "${model%-repeat}" in
            whisper|shipping-zh) repo=mlx-community/whisper-large-v3-mlx; rev=49e6aa286ad60c14352c404340ded53710378a11;;
            turbo) repo=mlx-community/whisper-large-v3-turbo-q4; rev=660c343bbf4e52ac257f0b7d952e5388e6f93bef;;
            breeze) repo=eoleedi/Breeze-ASR-25-mlx; rev=172151e3fd93ab6dc841d639f23dd48b24bc8301;;
        esac
        if [[ "$model" = shipping-zh ]]; then language=zh; fi
        echo "$id / $model"
        prefix="$out/$id/$model"
        /usr/bin/time -l -o "$prefix.time" "$mlx/.venv/bin/python" "$mlx/run.py" "$out/$id/audio.wav" "$prefix.json" "$repo" "$language" --revision "$rev" > "$prefix.log" 2>&1
    done
done
