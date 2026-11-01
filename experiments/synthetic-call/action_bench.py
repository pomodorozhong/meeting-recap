"""Run paired full-recap and focused-action extraction on exact and transcribed synthetic calls."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

import numpy as np
from scipy.optimize import linear_sum_assignment

from collection import HERE, check_clean, digest, load
from score_case import time_stats

PIPE = HERE.parent / "pipelines/whisper-sortformer"
CASES = HERE / "action-scripts"


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def speaker_map(truth, predicted, names):
    """Maximum shared seconds under a one-to-one mapping. Surplus labels remain unmatched."""
    gold = sorted({s["speaker_id"] for s in truth})
    labels = sorted({s["speaker_id"] for s in predicted})
    weights = np.zeros((len(gold), len(labels)))
    for t in truth:
        for p in predicted:
            overlap = min(t["end_seconds"], p["end_seconds"]) - max(t["start_seconds"], p["start_seconds"])
            if overlap > 0:
                weights[gold.index(t["speaker_id"]), labels.index(p["speaker_id"])] += overlap
    rows, cols = linear_sum_assignment(weights, maximize=True)
    return {names[labels[j]]: gold[i] for i, j in zip(rows, cols) if weights[i, j] and labels[j] in names}


def extract(lines, run, mode, python):
    run.mkdir()
    write(run / "lines.json", lines)
    cmd = [python, PIPE / "summary_stage.py", run / "lines.json", run / "raw.json"]
    if mode == "focused":
        cmd.append("--actions-only")
    with (run / "stage.log").open("w") as log:
        subprocess.run(["/usr/bin/time", "-l", "-o", run / "stage.time", *cmd], check=True,
                       stdout=log, stderr=subprocess.STDOUT)
    raw = load(run / "raw.json")
    reply = re.sub(r"<think>.*?</think>", "", raw["replies"][-1]["reply"], flags=re.S)
    parsed = json.loads(reply[reply.index("{"):reply.rindex("}") + 1])
    items = parsed["action_items"]
    if not isinstance(items, list) or not all(isinstance(it, dict) for it in items):
        raise ValueError(f"malformed action_items in {run}")
    write(run / "items.json", items)
    return {**time_stats(run / "stage.time"), "model_revision": raw["model_revision"],
            "lines_sha256": digest(run / "lines.json"), "items_sha256": digest(run / "items.json")}


def run_case(script, collection, out):
    src = collection / script.stem
    check_clean(src, script)
    out.mkdir()
    audio = out / "pipeline"
    python = PIPE / ".venv/bin/python"
    subprocess.run([python, PIPE / "recap.py", "run", src / "call.wav", audio,
                    "--asr", "turbo-q4", "--diarizer", "sortformer", "--no-summary"], check=True)
    # Read exactly the named, timestamped lines supplied by the normal transcript renderer.
    lines = [f"[{t}] {who}: {text}" for t, who, text in re.findall(
        r"^\*\*\[([\d:]+)\] (.+?):\*\* (.*)$", (audio / "transcript.md").read_text(), re.M)]
    exact = []
    for t in load(src / "transcript.json")["segments"]:
        sec = int(t["start"])
        exact.append(f"[{sec//3600:02}:{sec//60%60:02}:{sec%60:02}] Speaker {t['speaker']}: {t['text']}")
    if not lines:
        raise ValueError(f"empty rendered transcript in {audio}")
    runs = {}
    mapping = speaker_map(load(src / "segments.json"), load(audio / "diarization.json"), load(audio / "speakers.json")["labels"])
    for source, inputs in (("exact", exact), ("audio", lines)):
        for mode in ("ordinary", "focused"):
            name = f"{source}-{mode}"
            print(f"[{script.stem}] {name}", flush=True)
            runs[name] = extract(inputs, out / name, mode, python)
    write(out / "case.json", {"script_sha256": digest(script), "audio_sha256": digest(src / "call.wav"),
                              "duration_seconds": load(src / "manifest.json")["duration_seconds"],
                              "audio_speaker_map": mapping, "runs": runs})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--collection", type=Path, default=HERE / "out")
    parser.add_argument("--case", choices=[s.stem for s in sorted(CASES.glob("*.json"))], action="append")
    args = parser.parse_args()
    root = args.results.resolve()
    if any((p / ".git").exists() for p in (root, *root.parents)):
        parser.error("results must be outside any Git checkout")
    root.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HUB_OFFLINE"] = "1"
    subprocess.run(["uv", "sync", "--locked", "--project", PIPE], check=True)
    for script in sorted(CASES.glob("*.json")):
        if not args.case or script.stem in args.case:
            run_case(script, args.collection, root / script.stem)
