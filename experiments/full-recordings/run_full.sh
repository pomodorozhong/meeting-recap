#!/bin/zsh
# Sortformer + Whisper Large v3 (Chinese forced) on full recordings.
# Env: WHISPERKIT_CLI, FLUIDAUDIO_CLI (fluidaudiocli built from FluidAudio ea50062), WHISPER_MODEL_DIR, OUT
# Args: 16 kHz mono WAV files
set -eu
W=${WHISPERKIT_CLI:?}; C=${FLUIDAUDIO_CLI:?}; M=${WHISPER_MODEL_DIR:?}; OUT=${OUT:?Set OUT to a private dataset run directory}
t() { name=$1; shift; mkdir -p $OUT/$name; { /usr/bin/time -l "$@" > $OUT/$name/stdout.txt; } 2> $OUT/$name/time.txt; echo "done $name"; }
for wav in "$@"; do
  r=$(basename $wav .wav)
  t sortformer_$r $C sortformer $wav --output $OUT/sortformer_$r.json
  t whisper_$r $W transcribe --audio-path $wav --model-path $M --language zh --use-prefill-prompt --chunking-strategy vad --word-timestamps --report --report-path $OUT/whisper_$r
done
