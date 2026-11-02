"""Transcribe verified source calls with pinned Whisper, reusing matching reports.

Usage: uv run --locked --project experiments/synthetic-call python
experiments/synthetic-call/transcribe_collection.py FIXTURES_ROOT RUNS_ROOT
Existing reports must match their audio, script, model and decoding settings.
Archive a stale report before intentionally decoding changed input again.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile
import time

from collection import SCRIPTS, build, digest, load

MODEL = {"repository": "mlx-community/whisper-large-v3-mlx",
         "revision": "49e6aa286ad60c14352c404340ded53710378a11"}
SETTINGS = {"temperature": 0.0, "condition_on_previous_text": False,
            "word_timestamps": False}


def validate_report(path, provenance):
    report = load(path)
    if not isinstance(report, dict) or any(report.get(key) != value for key, value in provenance.items()):
        raise ValueError(f"{path} has stale ASR provenance; archive it before decoding again")
    segments = report.get("segments")
    if (not isinstance(report.get("text"), str) or not isinstance(segments, list)
            or any(not isinstance(segment, dict) or not isinstance(segment.get("text"), str)
                   for segment in segments)):
        raise ValueError(f"{path} must contain text and segments")
    if report["text"].strip() != "".join(segment["text"] for segment in segments).strip():
        raise ValueError(f"{path} has inconsistent text and segments")
    return report


def publish_report(path, report, provenance):
    """Publish a complete JSON file without replacing an existing report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".asr-", suffix=".json", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        validate_report(temporary, provenance)
        try:
            os.link(temporary, path)
        except FileExistsError:
            validate_report(path, provenance)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def transcribe_collection(fixtures, runs):
    # Verify the entire collection before creating output or loading GPU models.
    build(fixtures, check_only=True)
    missing = []
    for name, script_path in SCRIPTS.items():
        language = load(script_path).get("language", "zh")
        provenance = {"audio_sha256": digest(fixtures / name / "call.wav"),
                      "script_sha256": digest(script_path), "model": MODEL,
                      "settings": {**SETTINGS, "language": language}}
        output = runs / name / "asr.json"
        if output.exists() or output.is_symlink():
            validate_report(output, provenance)
            print(f"reused ASR {name} ({language})", flush=True)
        else:
            missing.append((name, output, provenance))
    if not missing:
        return

    import mlx_whisper
    from huggingface_hub import snapshot_download

    model = snapshot_download(MODEL["repository"], revision=MODEL["revision"],
                              allow_patterns=["config.json", "weights.npz"])
    for name, output, provenance in missing:
        started = time.monotonic()
        result = mlx_whisper.transcribe(str(fixtures / name / "call.wav"),
                                       path_or_hf_repo=model, **provenance["settings"])
        report = {"text": result["text"], "segments": result["segments"], **provenance,
                  "elapsed_seconds": round(time.monotonic() - started, 3)}
        publish_report(output, report, provenance)
        print(f"completed ASR {name} ({provenance['settings']['language']}), "
              f"{report['elapsed_seconds']:.1f}s", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", type=Path, metavar="FIXTURES_ROOT")
    parser.add_argument("runs", type=Path, metavar="RUNS_ROOT")
    args = parser.parse_args()
    try:
        transcribe_collection(args.fixtures, args.runs)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
