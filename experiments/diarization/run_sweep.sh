#!/bin/zsh
# Community-1 settings sweep (5 repeats each) and the other FluidAudio diarizers on the excerpt.
# Build first: swift build -c release && swift build -c release --product fluidaudiocli
# Env: AUDIO (16 kHz mono WAV), OUT
set -eu
A=${AUDIO:?}; OUT=${OUT:?Set OUT to a private dataset run directory}; B=.build/release/diarexp; C=.build/release/fluidaudiocli
OUT=${OUT:A}
mkdir -p "${OUT:h}"
# Reserve this run atomically before starting a model; failed runs keep their partial outputs.
if ! mkdir "$OUT" 2>/dev/null; then
  print -u2 -- "OUT must be a new writable directory: $OUT"
  exit 2
fi
mkdir "$OUT/rep" "$OUT/other"
cfg() { n=$1; shift; for i in 1 2 3 4 5; do $B $A $OUT/rep/${n}__$i.json "$@" >/dev/null 2>&1; done; echo "done $n"; }
cfg default
cfg n3 num=3
cfg n3_excl_false num=3 excl=false
cfg n3_exovl_false num=3 exovl=false
cfg n3_minseg0.25 num=3 minseg=0.25
cfg n3_minseg0.25_excl_false num=3 minseg=0.25 excl=false
cfg n3_minseg0.5 num=3 minseg=0.5
cfg thr0.7 thr=0.7
cfg thr0.8 thr=0.8
cfg range2_5 min=2 max=5
$C sortformer $A --output $OUT/other/sortformer.json
for v in dihard3 ami callhome dihard2; do $C lseend $A --variant $v --output $OUT/other/lseend_$v.json; done
raw_names=(sortformer lseend_dihard3 lseend_ami lseend_callhome lseend_dihard2)
for name in "${raw_names[@]}"; do
  python3 sortformer_to_segments.py "$OUT/other/$name.json" "$OUT/other/${name}_seg.json"
done
# Register each run with dataset.py, then evaluate against a confirmed reference snapshot.
