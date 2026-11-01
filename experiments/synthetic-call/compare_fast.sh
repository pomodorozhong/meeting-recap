#!/bin/bash
# Finish a base case with the compact ASR and the turn-order evaluations. Inputs are synthetic.
set -euo pipefail
if [[ $# != 2 ]]; then echo "usage: compare_fast.sh RECORDING_DIR COMPLETED_CASE_DIR" >&2; exit 2; fi
here=$(cd "$(dirname "$0")" && pwd)
mlx=$(dirname "$here")/mlx
source_dir=$(cd "$1" && pwd)
out=$(cd "$2" && pwd)
test -s "$out/scores.json" || { echo "complete the base case first" >&2; exit 2; }
if ! mkdir "$out/extension"; then echo "preserve the existing extension in another folder before retrying" >&2; exit 2; fi
export HF_HUB_OFFLINE=1
pipe=$(dirname "$here")/pipelines/whisper-sortformer
/usr/bin/time -l -o "$out/extension/turbo.time" "$mlx/.venv/bin/python" "$mlx/run.py" \
    "$out/pipeline/audio.wav" "$out/extension/turbo.json" mlx-community/whisper-large-v3-turbo-q4 zh \
    --revision 660c343bbf4e52ac257f0b7d952e5388e6f93bef >"$out/extension/turbo.log" 2>&1
if [[ $(basename "$out") != silence ]]; then
    uv run --locked --project "$here" "$here/turn_order.py" "$source_dir" "$out" "$out/extension/review" >"$out/extension/turn-order.json"
fi
case "$(basename "$out")" in
    handoff|logistics)
        oracle="$out/extension/exact-script"
        mkdir "$oracle"
        uv run --locked --project "$here" python - "$source_dir/transcript.json" "$oracle" <<'CODE'
import json, sys
from pathlib import Path
source, out = map(Path, sys.argv[1:])
turns = [{"speaker_id": t["speaker"], "text": t["text"], "start_seconds": t["start"], "end_seconds": t["end"]}
         for t in json.loads(source.read_text())["segments"]]
(out / "turns.json").write_text(json.dumps(turns, ensure_ascii=False))
(out / "speakers.json").write_text(json.dumps({"labels": {t["speaker_id"]: "Speaker " + t["speaker_id"] for t in turns}}))
CODE
        uv run --locked --project "$pipe" "$pipe/recap.py" summarize "$oracle"
        fast="$out/extension/fast-pipeline"
        uv run --locked --project "$pipe" "$pipe/recap.py" run "$source_dir/call.wav" "$fast" --asr turbo-q4 --diarizer who
        uv run --locked --project "$here" "$here/score_speakers.py" --reference "$source_dir" --audio "$source_dir/call.wav" \
            --segments "$fast/diarization.json" --asr "$fast/asr.json" --turns "$fast/turns.json" --json >"$fast/speakers-score.json"
        ;;
esac
case "$(basename "$out")" in
    handoff|silence)
        repeat="$out/extension/repeats"
        mkdir "$repeat"
        for n in 2 3; do
            for model in whisper breeze turbo-q4; do
                file="$repeat/$model-$n"
                case "$model" in
                    whisper) cmd=("$pipe/.venv/bin/python" "$pipe/asr_stage.py") ;;
                    *) cmd=("$mlx/.venv/bin/python" "$mlx/run.py") ;;
                esac
                cmd+=("$out/pipeline/audio.wav" "$file.json")
                case "$model" in
                    breeze) cmd+=(eoleedi/Breeze-ASR-25-mlx zh) ;;
                    turbo-q4) cmd+=(mlx-community/whisper-large-v3-turbo-q4 zh --revision 660c343bbf4e52ac257f0b7d952e5388e6f93bef) ;;
                esac
                /usr/bin/time -l -o "$file.time" "${cmd[@]}" >"$file.log" 2>&1
            done
        done
        ;;
esac
uv run --locked --project "$here" "$here/score_case.py" "$source_dir" "$out" >"$out/extension/scores.partial"
mv "$out/extension/scores.partial" "$out/extension/scores.json"
