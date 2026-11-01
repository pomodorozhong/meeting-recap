"""Test a five-second exact-digital-silence gate on the collection's 16 kHz mono PCM16."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np
from opencc import OpenCC
import soundfile as sf

from collection import HERE, RATE, digest, load
from score_case import edit_distance, normalize, time_stats
from score_speakers import words


def chunks(pcm, rate=RATE):
    """Return half-open sample spans. Keep 250 ms of context bordering each long zero run."""
    active = np.flatnonzero(pcm)
    if not active.size:
        return []
    minimum = 5 * rate
    groups = np.split(active, np.flatnonzero(np.diff(active) > minimum) + 1)
    spans = []
    for group in groups:
        first, last = int(group[0]), int(group[-1] + 1)
        start = 0 if first < minimum else first - rate // 4
        end = len(pcm) if len(pcm) - last < minimum else last + rate // 4
        spans.append((start, end))
    return spans


def transcribe(name, wav, path):
    mlx = HERE.parent / "mlx"
    pipe = HERE.parent / "pipelines/whisper-sortformer"
    if name == "whisper":
        cmd = [pipe / ".venv/bin/python", pipe / "asr_stage.py", wav, path]
    else:
        cmd = [mlx / ".venv/bin/python", mlx / "run.py", wav, path]
        if name == "breeze":
            cmd.extend(["eoleedi/Breeze-ASR-25-mlx", "zh"])
        else:
            cmd.extend(["mlx-community/whisper-large-v3-turbo-q4", "zh", "--revision",
                        "660c343bbf4e52ac257f0b7d952e5388e6f93bef"])
    timing = path.with_suffix(".time")
    with path.with_suffix(".log").open("w") as log:
        subprocess.run(["/usr/bin/time", "-l", "-o", timing, *cmd], check=True, stdout=log, stderr=subprocess.STDOUT,
                       env={**os.environ, "HF_HUB_OFFLINE": "1"})
    return load(path), time_stats(timing)


def run(source, case_dir):
    manifest = load(source / "manifest.json")
    if digest(source / "call.wav") != manifest["call_sha256"] or manifest["call_sha256"] != (
            case_dir / "input.sha256").read_text().strip():
        raise ValueError("different benchmark audio")
    wav = source / "call.wav"
    info = sf.info(wav)
    if (info.samplerate, info.channels, info.subtype) != (RATE, 1, "PCM_16"):
        raise ValueError("expected synthetic 16 kHz mono PCM16")
    started = time.monotonic()
    pcm, _ = sf.read(wav, dtype="int16")
    spans = chunks(pcm)
    out = case_dir / "silence-split"
    out.mkdir()
    converted = []
    for i, (a, b) in enumerate(spans):
        if (a, b) != (0, len(pcm)):
            path = out / f"chunk-{i}.wav"
            sf.write(path, pcm[a:b].astype("float32") / 32768, RATE, subtype="FLOAT")
            converted.append((a / RATE, path))
    result = {"spans_seconds": [[a / RATE, b / RATE] for a, b in spans], "gate_seconds": time.monotonic() - started,
              "passthrough": spans == [(0, len(pcm))]}
    if not result["passthrough"]:
        convert = OpenCC("t2s").convert
        reference = normalize(load(source / "transcript.json")["text"], convert)
        turns = load(source / "segments.json")
        gaps = [(a["end_seconds"], b["start_seconds"]) for a, b in zip(turns, turns[1:])
                if b["start_seconds"] - a["end_seconds"] >= 5]
        result["asr"] = {}
        for name in ("whisper", "breeze", "turbo-q4"):
            joined = {"text": "", "segments": []}
            wall, peak = result["gate_seconds"], 0
            for i, (offset, path) in enumerate(converted):
                data, timing = transcribe(name, path, out / f"{name}-{i}.json")
                wall += timing["wall_seconds"]
                peak = max(peak, timing["peak_footprint_bytes"])
                joined["text"] += data["text"]
                for seg in data["segments"]:
                    for unit in [seg, *seg["words"]]:
                        unit["start"] += offset
                        unit["end"] += offset
                    joined["segments"].append(seg)
            (out / f"{name}.json").write_text(json.dumps(joined, ensure_ascii=False))
            errors = edit_distance(reference, normalize(joined["text"], convert))
            result["asr"][name] = {"errors": errors, "cer": errors / len(reference) if reference else None,
                                   "wall_seconds": wall, "peak_inference_footprint_bytes": peak if converted else None,
                                   "word_midpoints_in_long_gaps": sum(any(a < (s + e) / 2 < b for a, b in gaps)
                                                                       for s, e, _ in words(joined))}
    (out / "scores.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("case_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.case_dir), indent=2))
