#!/bin/bash
# Run one recording at a time. Raw outputs are outside Git. All paths may contain spaces.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
experiments=$(dirname "$here")
pipe="$experiments/pipelines/whisper-sortformer"
mlx="$experiments/mlx"
fluid="$pipe/.build/release/fluidaudiocli"
offline="$experiments/diarization/.build/release/diarexp"
export HF_HUB_OFFLINE=1
case "$#" in
    1) destination=$1 ;;
    3) destination=$2 ;;
    *) echo "usage: benchmark.sh RESULTS_ROOT | benchmark.sh COLLECTION_DIR RESULTS_ROOT CASE" >&2; exit 2 ;;
esac
root=$(python3 - "$destination" <<'CODE'
from pathlib import Path
import sys
path = Path(sys.argv[1]).resolve()
if any((p / ".git").exists() for p in (path, *path.parents)):
    sys.exit("results must be outside any Git checkout")
print(path)
CODE
)
if [[ $# == 1 ]]; then
    # The full sweep has one destination and uses the stock collection beside this script.
    uv run --locked --project "$here" "$here/collection.py" --suite baseline
    for id in handoff logistics handoff-channel logistics-overlap planning silence stocktake; do
        "$here/benchmark.sh" "$here/out" "$1" "$id"
        source_id="$id"
        [[ "$id" != planning ]] || source_id=script
        "$here/compare_fast.sh" "$here/out/$source_id" "$1/$id"
        uv run --locked --project "$here" "$here/silence_split.py" "$here/out/$source_id" "$1/$id"
    done
    exit 0
fi
collection=$(cd "$1" && pwd)
mkdir -p "$root"
id=$3
case "$id" in
    planning) source_dir="$collection/script" ;;
    handoff|handoff-channel|logistics|logistics-overlap|silence|stocktake) source_dir="$collection/$id" ;;
    *) echo "unknown recording: $id" >&2; exit 2 ;;
esac
out="$root/$id"
wav="$source_dir/call.wav"
# Atomically reserve a fresh case folder. A failed run keeps its logs.
mkdir "$out"
python3 - "$source_dir" "$out" <<'PY'
from pathlib import Path
import hashlib, json, sys
source, out = map(Path, sys.argv[1:])
sha = hashlib.sha256((source / "call.wav").read_bytes()).hexdigest()
if sha != json.loads((source / "manifest.json").read_text())["call_sha256"]:
    sys.exit("recording digest mismatch")
(out / "input.sha256").write_text(sha + "\n")
PY
timed() {
    local name=$1
    shift
    echo "[$id] $name"
    /usr/bin/time -l -o "$out/$name.time" "$@" >"$out/$name.log" 2>&1 || { tail -8 "$out/$name.log" >&2; return 1; }
}
# Invoke the existing pipeline for the baseline, sharing its saved ASR and diarization.
pipeline_cmd=(uv run --locked --project "$pipe" "$pipe/recap.py" run "$wav" "$out/pipeline")
if [[ "$id" != handoff && "$id" != logistics ]]; then pipeline_cmd+=(--no-summary); fi
timed pipeline "${pipeline_cmd[@]}"
audio="$out/pipeline/audio.wav"
# Sync outside the timed part so wall times are inference process startup + load + decode.
uv sync --locked --project "$mlx" --quiet
timed breeze "$mlx/.venv/bin/python" "$mlx/run.py" "$audio" "$out/breeze.json" eoleedi/Breeze-ASR-25-mlx zh
# Check the same pinned weight bytes as the release pipeline before calling the Swift binary directly.
(cd "$pipe" && python3 -c 'import pins; pins.check_weights("who")')
timed who "$pipe/.build/release/who-diarize" "$audio" "$out/who.json" "${WHO_MODELS:-$HOME/Library/Application Support/meeting-recap/who}"
if [[ "$id" == handoff || "$id" == logistics ]]; then
    count=2
    [[ "$id" != logistics ]] || count=4
    (cd "$pipe" && python3 - <<'PY'
import pins
for folder, sha in (
    ("ls-eend", "d375290fbaf031b22ee72cd4539f781bbf0c58add15fc64c457c3be89610ba04"),
    ("speaker-diarization", "94e171fd88406ba786232eb86860767185a57b47d89bda6dc8dd8b914563dafb"),
):
    if pins.tree_sha256(pins.SORTFORMER_MODELS.parent / folder) != sha:
        raise SystemExit(f"missing or changed {folder} model cache")
PY
    )
    timed community "$offline" "$audio" "$out/community.json"
    timed community-count "$offline" "$audio" "$out/community-count.json" "num=$count"
    for variant in dihard3 ami callhome dihard2; do
        name="lseend-$variant"
        timed "$name" "$fluid" lseend "$audio" --variant "$variant" --output "$out/$name.raw.json"
        python3 "$experiments/diarization/sortformer_to_segments.py" "$out/$name.raw.json" "$out/$name.json"
    done
fi
uv run --locked --project "$here" "$here/score_case.py" "$source_dir" "$out" > "$out/scores.partial"
mv "$out/scores.partial" "$out/scores.json"
