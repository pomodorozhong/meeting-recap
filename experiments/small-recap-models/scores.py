"""Collect the measurements and, once graded, the verdicts of a run into one JSON of counts and digests.

    uv run --project experiments/small-recap-models experiments/small-recap-models/scores.py OUT > scores.json

Reads OUT/<case>/<run>/run.json, OUT/<run>.time (from /usr/bin/time -l) and, if present, OUT/judgments.json:

    {"<case>": {"<run>": {"verdicts": ["full" | "partial" | "wrong_or_absent", ...],
                            "supported": [true | false, ...],
                            "reopens_settled_issue": bool, "unsupported_or_garbled_detail": bool,
                            "summary_sha256": "<sha256 of summary.md that was graded>", "notes": "..."}}}

A run whose reply wasn't readable JSON scores zero without a judgment. "supported" says, per check, whether the lines the recap cites for that fact support it. A verdict counts only
while summary_sha256 matches the summary.md on disk, so changed text never inherits an earlier grade. The output
holds no recap or transcript text, so it can be committed; the judgments' "notes" stay out of it.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

from run import CASES, MODELS, run_id

RUNS = [run_id(name, thinking) for thinking in (False, True) for name in MODELS]

CHECKS = {"onboarding": 4, "english-audit": 5}


def time_stats(path):
    if not path.is_file():
        return None
    text = path.read_text()
    real = re.search(r"([\d.]+) real", text)
    peak = re.search(r"(\d+)\s+peak memory footprint", text)
    rss = re.search(r"(\d+)\s+maximum resident set size", text)
    return {"process_seconds": float(real.group(1)) if real else None,
            "peak_footprint_bytes": int(peak.group(1)) if peak else None,
            "max_rss_bytes": int(rss.group(1)) if rss else None}


def grade(judgment, summary, checks, failed=False):
    if failed:  # an unreadable reply scores zero on its call, as the plan says
        return {"graded": True, "failed": True, "verdicts": ["wrong_or_absent"] * checks, "supported": [False] * checks,
                "full": 0, "partial": 0, "full_and_supported": 0, "reopens_settled_issue": False,
                "unsupported_or_garbled_detail": False, "summary_sha256": None}
    if judgment is None:
        return {"graded": False}
    if summary is None or hashlib.sha256(summary.read_bytes()).hexdigest() != judgment["summary_sha256"]:
        return {"graded": False, "stale": True}
    verdicts, supported = judgment["verdicts"], judgment["supported"]
    if len(verdicts) != checks or len(supported) != checks:
        raise ValueError(f"expected {checks} verdicts and support flags")
    return {"graded": True, "verdicts": verdicts, "supported": supported,
            "full": verdicts.count("full"), "partial": verdicts.count("partial"),
            "full_and_supported": sum(v == "full" and s for v, s in zip(verdicts, supported)),
            "reopens_settled_issue": judgment["reopens_settled_issue"],
            "unsupported_or_garbled_detail": judgment["unsupported_or_garbled_detail"],
            "summary_sha256": judgment["summary_sha256"]}


def main(out):
    out = Path(out)
    judgments_path = out / "judgments.json"
    judgments = json.loads(judgments_path.read_text()) if judgments_path.is_file() else {}
    result = {"models": {}, "cases": {}}
    for name, (repo, revision, loader) in MODELS.items():
        result["models"][name] = {"repo": repo, "revision": revision, "loader": loader}
    result["processes"] = {name: time_stats(out / f"{name}.time") for name in RUNS}
    for case in CASES:
        inputs = out / case / "inputs.json"
        if not inputs.is_file():
            continue
        entry = {"inputs": json.loads(inputs.read_text()), "checks": CHECKS[case], "runs": {}}
        for name in RUNS:
            run_path = out / case / name / "run.json"
            if not run_path.is_file():
                continue
            run = json.loads(run_path.read_text())
            summary = out / case / name / "summary.md"
            entry["runs"][name] = {
                "status": run["status"], "reason": run.get("reason"), "seconds": round(run["seconds"], 2),
                "thinking": run.get("thinking", False), "max_tokens": run.get("max_tokens"),
                "mlx_peak_bytes": run["mlx_peak_bytes"], "chunks": run["chunks"],
                "prompt_tokens": [r["prompt_tokens"] for r in run["replies"]],
                "reply_tokens": [r["reply_tokens"] for r in run["replies"]],
                "evidence": run.get("evidence"),
                "summary_sha256": hashlib.sha256(summary.read_bytes()).hexdigest() if summary.is_file() else None,
                "grade": grade(judgments.get(case, {}).get(name), summary if summary.is_file() else None,
                               CHECKS[case], failed=run["status"] == "failed"),
            }
        result["cases"][case] = entry
    json.dump(result, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main(*sys.argv[1:2])
