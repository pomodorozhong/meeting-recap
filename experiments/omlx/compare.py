"""Compare the stage's, the control's and oMLX's replies, and collect times and memory, into counts and digests.

    uv run --project experiments/omlx experiments/omlx/compare.py OUT > OUT/results.json

Reads OUT/<call>/{stage,control,omlx}.json, their .time reports from /usr/bin/time -l, and omlx-models.json. The
output holds no transcript or reply text, so it can be committed.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

from common import CALLS

RUNNERS = ("stage", "control", "omlx")


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def first_difference(a, b):
    """Index of the first differing character, or None if the strings are equal."""
    if a == b:
        return None
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


def time_stats(path):
    if not path.is_file():
        return None
    text = path.read_text()
    real = re.search(r"([\d.]+) real", text)
    peak = re.search(r"(\d+)\s+peak memory footprint", text)
    return {"process_seconds": float(real.group(1)) if real else None,
            "peak_footprint_bytes": int(peak.group(1)) if peak else None}


def compare_call(folder):
    runs = {name: json.loads((folder / f"{name}.json").read_text()) for name in RUNNERS
            if (folder / f"{name}.json").is_file()}
    entry = {"runs": {}}
    for name, run in runs.items():
        entry["runs"][name] = {
            "process": time_stats(folder / f"{name}.time"),
            "mlx_peak_bytes": run.get("mlx_peak_bytes"),
            "replies": [{k: r.get(k) for k in ("attempt", "seconds", "prompt_tokens", "completion_tokens",
                                                "cached_tokens", "time_to_first_token", "model_load_seconds",
                                                "finish_reason", "model")}
                        | {"reply_sha256": digest(r["reply"]), "reply_characters": len(r["reply"]),
                           "has_thinking_text": bool(r.get("reasoning")) or "<think>" in r["reply"]
                           or "</think>" in r["reply"]}
                        for r in run["replies"]],
        }
    stage = runs.get("stage", {}).get("replies", [{}])[0].get("reply")
    control = runs.get("control", {}).get("replies", [{}])[0].get("reply")
    omlx = [r["reply"] for r in runs.get("omlx", {}).get("replies", [])]
    entry["omlx_first_matches_stage"] = bool(omlx) and stage is not None and omlx[0] == stage
    entry["omlx_first_differs_from_stage_at"] = first_difference(omlx[0], stage) if omlx and stage else None
    entry["control_matches_stage"] = control is not None and control == stage
    entry["omlx_first_matches_control"] = bool(omlx) and control is not None and omlx[0] == control
    entry["omlx_repeat_matches_first"] = len(omlx) > 1 and all(r == omlx[0] for r in omlx[1:])
    models = folder / "omlx-models.json"
    entry["omlx_models"] = sorted(m.get("id") for m in json.loads(models.read_text()).get("data", [])) \
        if models.is_file() else None
    return entry


def main(out):
    out = Path(out)
    calls = {call: compare_call(out / call) for call in CALLS if (out / call).is_dir()}
    every = list(calls.values())
    omlx_runs = [c["runs"].get("omlx") for c in every]
    checks = {
        "same_output": bool(every) and all(c["omlx_first_matches_stage"] for c in every),
        "pinned_revision": bool(every) and all(c["omlx_models"] == ["qwen3.5-9b"] for c in every),
        "memory_readable": bool(every) and all(r and (r["process"] or {}).get("peak_footprint_bytes")
                                               for r in omlx_runs),
        "thinking_off": bool(every) and all(r and not any(x["has_thinking_text"] for x in r["replies"])
                                            for r in omlx_runs),
    }
    json.dump({"checks": checks, "calls": calls}, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main(*sys.argv[1:2])
