# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["mlx-whisper==0.4.2"]
# ///
"""Transcribe a 16 kHz WAV with an MLX Whisper-format model and write WhisperKit-shaped JSON.

Usage: run.py <wav> <out.json> <hf-repo> [language]
Repos used: mlx-community/whisper-large-v3-mlx, eoleedi/Breeze-ASR-25-mlx.
"""
import json, sys, time
import mlx_whisper

wav, out, repo = sys.argv[1:4]
language = sys.argv[4] if len(sys.argv) > 4 else "zh"
t = time.time()
res = mlx_whisper.transcribe(wav, path_or_hf_repo=repo, language=language, task="transcribe",
                             word_timestamps=True, condition_on_previous_text=False)
elapsed = time.time() - t
segments = [{"start": s["start"], "end": s["end"], "text": s["text"],
             "words": [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in s.get("words", [])]}
            for s in res["segments"]]
json.dump({"text": res["text"], "elapsed": elapsed, "model": repo, "language": language, "segments": segments},
          open(out, "w"), ensure_ascii=False, indent=1)
print(f"{repo} {elapsed:.1f}s segments={len(segments)}")
