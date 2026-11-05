"""Run recap settings on three synthetic calls, write blinded grading sheets, and count the grades.

Usage: collection_recap_pairs.py FIXTURES PAIRS [--report]

FIXTURES is the verified synthetic collection and PAIRS a new absolute folder outside Git. Without --report this
runs every setting on every call through the pipeline (rerunning the command skips finished runs), then writes
PAIRS/grading/<call>.md with the recaps under letters, PAIRS/key.json (which letter is which setting) and an empty
PAIRS/grades.json. Fill in grades.json by hand, then run with --report to check it is complete and write
PAIRS/report.json. The plan is in docs/experiments/2026-11-06-recap-recognizer-vs-diarizer.md.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from collection import build, digest, load

HERE = Path(__file__).resolve().parent
PIPE = HERE.parent / "pipelines" / "whisper-sortformer"
CHECKS = load(HERE / "reference/recap-checks.json")["calls"]
SETTINGS = {
    "whisper-sortformer": [],
    "turbo-sortformer": ["--asr", "turbo-q4"],
    "whisper-who": ["--diarizer", "who"],
    "turbo-who": ["--asr", "turbo-q4", "--diarizer", "who"],
}
VERDICTS = ("full", "partial", "wrong_or_absent")
STAMP = re.compile(r"\d\d:\d\d:\d\d")


def commit():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()


def run(fixtures, pairs):
    if any((p / ".git").exists() for p in [pairs, *pairs.parents]):
        raise ValueError("PAIRS must be outside Git")
    build(fixtures, check_only=True)
    marker = pairs / "batch.json"
    if pairs.exists() and not marker.exists():
        raise ValueError("PAIRS exists but is not a folder this script started; choose a new path")
    pairs.mkdir(parents=True, exist_ok=True)
    if not marker.exists():
        marker.write_text(json.dumps({"code_commit": commit(), "settings": SETTINGS, "calls": list(CHECKS)}, indent=2))
    for call, info in CHECKS.items():
        for name, options in SETTINGS.items():
            folder = pairs / call / name
            if (folder / "summary.json").exists():
                continue
            resume = ["--resume"] if folder.exists() else []
            print(f"== {call} / {name}", flush=True)
            subprocess.run([PIPE / ".venv/bin/python", PIPE / "recap.py", "run", fixtures / call / "call.wav", folder,
                            "--language", info["language"], *options, *resume],
                           check=True, env={**os.environ, "HF_HUB_OFFLINE": "1"})
    sheets(pairs)


def cited_lines(folder, recap):
    transcript = (folder / "transcript.md").read_text(encoding="utf-8").splitlines()
    lines = []
    for stamp in dict.fromkeys(STAMP.findall(recap)):
        lines += [f"- {line.replace('**', '')}" for line in transcript if line.startswith(f"**[{stamp}]")]
    return lines


def sheets(pairs):
    batch = load(pairs / "batch.json")
    key, grades = {}, {}
    (pairs / "grading").mkdir(exist_ok=True)
    for call, info in CHECKS.items():
        # A fixed order by hash hides which setting is which without needing a random seed.
        order = sorted(batch["settings"], key=lambda s: hashlib.sha256(f"7/{call}/{s}".encode()).hexdigest())
        key[call] = {chr(65 + i): name for i, name in enumerate(order)}
        grades[call] = {label: {"verdicts": [None] * len(info["checks"]), "supported": [None] * len(info["checks"]),
                                "reopens_settled_issue": None, "unsupported_or_garbled_detail": None}
                        for label in key[call]}
        text = [f"# Grading sheet: {call}", "",
                "For each recap, grade every check **full**, **partial** or **wrong_or_absent**, and say whether a line "
                "the recap cites supports it (`supported`). Also say whether the recap reopens a question the call "
                "settled, and whether it contains unsupported or garbled detail. Put the answers in `grades.json`.", "",
                "Checks, in the order of the `verdicts` and `supported` lists:", ""]
        text += [f"{n + 1}. {check}" for n, check in enumerate(info["checks"])]
        for label, name in key[call].items():
            folder = pairs / call / name
            recap = (folder / "summary.md").read_text(encoding="utf-8")
            text += ["", f"## Recap {label}", "", recap, "", f"### Lines cited by recap {label}", ""]
            text += cited_lines(folder, recap) or ["(none)"]
        (pairs / "grading" / f"{call}.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    for name, content in (("key.json", key), ("grades.json", grades)):
        if not (pairs / name).exists():
            (pairs / name).write_text(json.dumps(content, indent=2) + "\n")
    print(f"Grading sheets are in {pairs / 'grading'}. Fill in {pairs / 'grades.json'}, then rerun with --report.")


def report(pairs):
    key, grades = load(pairs / "key.json"), load(pairs / "grades.json")
    rows = {}
    for call, info in CHECKS.items():
        for label, name in key[call].items():
            g = grades[call][label]
            n = len(info["checks"])
            if (len(g["verdicts"]) != n or len(g["supported"]) != n or any(v not in VERDICTS for v in g["verdicts"])
                    or any(not isinstance(s, bool) for s in g["supported"])
                    or not isinstance(g["reopens_settled_issue"], bool)
                    or not isinstance(g["unsupported_or_garbled_detail"], bool)):
                raise ValueError(f"grades for {call} recap {label} are incomplete")
            folder = pairs / call / name
            summary = load(folder / "summary.json")
            rows.setdefault(call, {})[name] = {
                **g, "summary_md_sha256": digest(folder / "summary.md"),
                "transcript_sha256": digest(folder / "transcript.md"),
                "line_count": len(load(folder / "turns.json")), "citation_checks": summary["checks"],
                "summary_seconds": load(folder / "stages.json")["summary"]["seconds"]}
    (pairs / "report.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(f"{'setting':30} {'fully correct':>14} {'with citations':>15} {'uncited':>8} {'invalid':>8} {'reopened':>9} {'unsupported':>12}")
    for name in SETTINGS:
        full = sum(v == "full" for c in rows.values() for v in c[name]["verdicts"])
        cited = sum(v == "full" and s for c in rows.values() for v, s in zip(c[name]["verdicts"], c[name]["supported"]))
        uncited = sum(c[name]["citation_checks"]["items_without_evidence"] for c in rows.values())
        invalid = sum(c[name]["citation_checks"]["evidence_dropped"] for c in rows.values())
        reopened = sum(c[name]["reopens_settled_issue"] for c in rows.values())
        garbled = sum(c[name]["unsupported_or_garbled_detail"] for c in rows.values())
        total = sum(len(i["checks"]) for i in CHECKS.values())
        print(f"{name:30} {full:>11}/{total:<2} {cited:>12}/{total:<2} {uncited:>8} {invalid:>8} {reopened:>9} {garbled:>12}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", type=Path)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("--report", action="store_true", help="check the filled-in grades and write report.json")
    args = parser.parse_args()
    if not args.pairs.is_absolute():
        sys.exit("PAIRS must be an absolute path")
    if args.report:
        report(args.pairs)
    else:
        run(args.fixtures.resolve(), args.pairs)
