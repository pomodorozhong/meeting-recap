#!/bin/zsh
# Transcription variants on the 10-minute excerpt with WhisperKit's CLI (WhisperKit 0.18.0, e2adabb).
# Env: WHISPERKIT_CLI, WHISPER_MODEL_DIR (Core ML openai_whisper-large-v3 folder), AUDIO (16 kHz mono WAV), OUT
# Optional: MEETING_RECAP_CONTEXT_PROMPT and MEETING_RECAP_NAME_PROMPT add private, meeting-specific prompt runs.
set -eu
W=${WHISPERKIT_CLI:?}; M=${WHISPER_MODEL_DIR:?}; A=${AUDIO:?}; OUT=${OUT:?Set OUT to a private dataset run directory}
CONTEXT_PROMPT=${MEETING_RECAP_CONTEXT_PROMPT:-}
NAME_PROMPT=${MEETING_RECAP_NAME_PROMPT:-}
run() { name=$1; shift; mkdir -p $OUT/$name; { /usr/bin/time -l $W transcribe --audio-path $A --report --report-path $OUT/$name --word-timestamps "$@" > $OUT/$name/stdout.txt; } 2> $OUT/$name/time.txt; echo "done $name"; }
run zh_vad --model-path $M --language zh --use-prefill-prompt --chunking-strategy vad
run detect_vad --model-path $M --chunking-strategy vad
if [[ -n "$CONTEXT_PROMPT" ]]; then
  run zh_prompt_vad --model-path $M --language zh --use-prefill-prompt --chunking-strategy vad --prompt "$CONTEXT_PROMPT"
fi
if [[ -n "$NAME_PROMPT" ]]; then
  run zh_names_vad --model-path $M --language zh --use-prefill-prompt --chunking-strategy vad --prompt "$NAME_PROMPT"
fi
run zh_none --model-path $M --language zh --use-prefill-prompt
run zh_vad_speakerkit --model-path $M --language zh --use-prefill-prompt --chunking-strategy vad --diarization --diarization-num-speakers 3
run turbo_zh_vad --model large-v3-v20240930_turbo --download-model-path $OUT/models --language zh --use-prefill-prompt --chunking-strategy vad
