"""Transcribe a WAV using an exact Hugging Face snapshot and write WhisperKit-shaped JSON."""
import argparse
import json
from pathlib import Path
import re
import sys
import time

MODELS = {
    "mlx-community/whisper-large-v3-mlx": "49e6aa286ad60c14352c404340ded53710378a11",
    "eoleedi/Breeze-ASR-25-mlx": "172151e3fd93ab6dc841d639f23dd48b24bc8301",
}


def revision(value):
    if not re.fullmatch(r"[0-9a-fA-F]{40}", value):
        raise argparse.ArgumentTypeError("revision must be a full 40-character commit SHA")
    return value.lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav")
    parser.add_argument("out")
    parser.add_argument("repo")
    parser.add_argument("language", nargs="?", default="zh")
    parser.add_argument("--revision", type=revision, help="required for a model not listed in docs/runners.md")
    args = parser.parse_args()
    pin = args.revision or MODELS.get(args.repo)
    if pin is None:
        parser.error("an unlisted model requires --revision with its full commit SHA")

    from huggingface_hub import snapshot_download
    import mlx_whisper

    model_path = snapshot_download(repo_id=args.repo, revision=pin)
    if Path(model_path).name != pin:
        raise ValueError("downloaded model snapshot does not match the requested revision")
    started = time.time()
    result = mlx_whisper.transcribe(args.wav, path_or_hf_repo=model_path, language=args.language,
                                    task="transcribe", word_timestamps=True, condition_on_previous_text=False)
    elapsed = time.time() - started
    segments = [{"start": s["start"], "end": s["end"], "text": s["text"],
                 "words": [{"word": w["word"], "start": w["start"], "end": w["end"]}
                           for w in s.get("words", [])]} for s in result["segments"]]
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump({"text": result["text"], "elapsed": elapsed, "model": args.repo, "model_revision": pin,
                   "language": args.language, "segments": segments}, handle, ensure_ascii=False, indent=1)
    print(f"{args.repo}@{pin} {elapsed:.1f}s segments={len(segments)}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        sys.exit(str(error))
