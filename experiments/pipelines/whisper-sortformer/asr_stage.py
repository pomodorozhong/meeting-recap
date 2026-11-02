"""ASR stage: Whisper Large v3 through MLX, explicit spoken language, word timestamps, WhisperKit-shaped JSON.

Runs in its own process so the model's memory is released before the next stage.
"""
import json
import sys
import time

from pins import ASR_MODELS, mlx_peak_bytes, snapshot


def main(wav, out, language="zh", model="large-v3"):
    import mlx_whisper

    repo, revision = ASR_MODELS[model]
    path = snapshot(repo, revision)
    started = time.time()
    result = mlx_whisper.transcribe(wav, path_or_hf_repo=path, language=language, task="transcribe",
                                    word_timestamps=True, condition_on_previous_text=False)
    elapsed = time.time() - started
    segments = [{"start": s["start"], "end": s["end"], "text": s["text"],
                 "words": [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in s.get("words", [])]}
                for s in result["segments"]]
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"model": repo, "model_revision": revision, "language": language,
                   "settings": {"word_timestamps": True, "condition_on_previous_text": False},
                   "elapsed_seconds": elapsed, "mlx_peak_bytes": mlx_peak_bytes(),
                   "text": result["text"], "segments": segments}, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
