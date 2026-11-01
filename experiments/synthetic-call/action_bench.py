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


def accepted_items(accepted, candidates, lines):
    """Only the verifier's IDs and line numbers can affect the original candidate list."""
    if not isinstance(accepted, list):
        raise ValueError("expected a list of accepted IDs")
    seen, kept = set(), []
    for row in accepted:
        n, refs = row["id"], row["lines"]
        if type(n) is not int or not 1 <= n <= len(candidates) or n in seen:
            raise ValueError(f"invalid or duplicate candidate ID: {n}")
        if not isinstance(refs, list) or not refs or any(type(i) is not int or not 1 <= i <= len(lines) for i in refs):
            raise ValueError(f"invalid supporting line numbers for candidate {n}")
        seen.add(n)
        stamps = list(dict.fromkeys(lines[i-1][1:9] for i in refs))
        kept.append({**candidates[n-1], "evidence": stamps})
    return kept


def extract(lines, run, mode, python, candidates_path=None):
    run.mkdir()
    write(run / "lines.json", lines)
    cmd = [python, PIPE / "summary_stage.py", run / "lines.json", run / "raw.json"]
    if mode == "focused":
        cmd.append("--actions-only")
    if candidates_path is not None:
        candidates = load(candidates_path)
        if not candidates:
            write(run / "items.json", [])
            return {"wall_seconds": 0.0, "peak_footprint_bytes": 0, "skipped_empty": True,
                    "lines_sha256": digest(run / "lines.json"), "items_sha256": digest(run / "items.json")}
        cmd.extend(["--verify-actions", candidates_path])
    with (run / "stage.log").open("w") as log:
        subprocess.run(["/usr/bin/time", "-l", "-o", run / "stage.time", *cmd], check=True,
                       stdout=log, stderr=subprocess.STDOUT)
    raw = load(run / "raw.json")
    reply = re.sub(r"<think>.*?</think>", "", raw["replies"][-1]["reply"], flags=re.S)
    parsed = json.loads(reply[reply.index("{"):reply.rindex("}") + 1])
    items = (parsed["action_items"] if candidates_path is None
             else accepted_items(parsed["accepted"], candidates, lines))
    if not isinstance(items, list) or not all(isinstance(it, dict) for it in items):
        raise ValueError(f"malformed action_items in {run}")
    write(run / "items.json", items)
    return {**time_stats(run / "stage.time"), "model_revision": raw["model_revision"],
            "lines_sha256": digest(run / "lines.json"), "items_sha256": digest(run / "items.json")}


def relabel_lines(lines, turns, truth):
    corrected = []
    for line, turn in zip(lines, turns, strict=True):
        seconds = int(turn["start_seconds"])
        stamp = f"[{seconds//3600:02}:{seconds//60%60:02}:{seconds%60:02}]"
        if not line.startswith(stamp + " "):
            raise ValueError("displayed line and ASR turn start differ")
        overlaps = {}
        for ref in truth:
            duration = min(turn["end_seconds"], ref["end_seconds"]) - max(turn["start_seconds"], ref["start_seconds"])
            if duration > 0:
                speaker = ref["speaker_id"]
                overlaps[speaker] = overlaps.get(speaker, 0.0) + duration
        label = "Speaker " + max(overlaps, key=overlaps.get) if overlaps else "Unknown speaker"
        _, text = line.split(": ", 1)
        corrected.append(f"{stamp} {label}: {text}")
    return corrected


def run_labels(script, collection, out):
    src = collection / script.stem
    check_clean(src, script)
    meta = load(out / "case.json")
    if meta["script_sha256"] != digest(script) or meta["audio_sha256"] != digest(src / "call.wav"):
        raise ValueError("the primary run belongs to different inputs")
    original = out / "audio-focused/lines.json"
    if digest(original) != meta["runs"]["audio-focused"]["lines_sha256"]:
        raise ValueError("the primary lines changed")
    lines = relabel_lines(load(original), load(out / "pipeline/turns.json"), load(src / "segments.json"))
    run = out / "labels-focused"
    print(f"[{script.stem}] labels-focused", flush=True)
    stats = extract(lines, run, "focused", PIPE / ".venv/bin/python")
    write(run / "run.json", stats)


def run_verifier(script, collection, out):
    meta = load(out / "case.json")
    primary = out / "audio-focused"
    source = meta["runs"]["audio-focused"]
    if meta["script_sha256"] != digest(script) or any(
        digest(primary / f"{key}.json") != source[f"{key}_sha256"] for key in ("items", "lines")
    ):
        raise ValueError("verifier inputs differ from the primary run")
    target = out / "audio-verified"
    print(f"[{script.stem}] audio-verified", flush=True)
    stats = extract(load(primary / "lines.json"), target, "verify", PIPE / ".venv/bin/python", primary / "items.json")
    write(target / "run.json", stats)


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
    phase = parser.add_mutually_exclusive_group()
    phase.add_argument("--labels-only", action="store_true", help="run registered label repair on completed primary outputs")
    phase.add_argument("--verify-only", action="store_true", help="verify citations in completed audio-focused outputs")
    args = parser.parse_args()
    root = args.results.resolve()
    if any((p / ".git").exists() for p in (root, *root.parents)):
        parser.error("results must be outside any Git checkout")
    root.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HUB_OFFLINE"] = "1"
    subprocess.run(["uv", "sync", "--locked", "--project", PIPE], check=True)
    for script in sorted(CASES.glob("*.json")):
        if not args.case or script.stem in args.case:
            run = run_labels if args.labels_only else run_verifier if args.verify_only else run_case
            run(script, args.collection, root / script.stem)
