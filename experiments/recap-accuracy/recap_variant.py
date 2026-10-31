#!/usr/bin/env python3
"""Recap one transcript with one recap variant through the pipeline's summary stage.

usage: recap_variant.py SOURCE OUT_DIR VARIANT

SOURCE is `script` (the synthetic call's own text and speakers), `script-relabeled` (the same, with the
speaker names rotated so A is called Speaker C, B Speaker A and C Speaker B), or a pipeline transcript.md.
VARIANT is one of the summary stage's variants (v0, v1, v2). It writes OUT_DIR/transcript.md, runs the
pipeline's summary_stage.py as a command (nothing is imported across experiment folders), and adds the
parsed notes to OUT_DIR/summary.json. A relabeled source also writes OUT_DIR/names.json for score.py.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PIPELINE = ROOT / "experiments" / "pipelines" / "whisper-sortformer"
REFERENCE = ROOT / "experiments" / "synthetic-call" / "reference" / "transcript.json"
SECTIONS = ("topics", "decisions", "action_items", "proposals", "open_questions")
ROTATION = {"A": "C", "B": "A", "C": "B"}


def stamp(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def script_lines(rotate):
    turns = json.loads(REFERENCE.read_text())["segments"]
    name = (lambda s: f"Speaker {ROTATION[s]}") if rotate else (lambda s: f"Speaker {s}")
    return [(stamp(t["start"]), name(t["speaker"]), t["text"]) for t in turns]


def transcript_lines(path):
    return re.findall(r"^\*\*\[(\d\d:\d\d:\d\d)\] (.+?):\*\* (.*)$", Path(path).read_text(), flags=re.M)


def main(source, out, variant):
    out = Path(out)
    if source in ("script", "script-relabeled"):
        rows = script_lines(source == "script-relabeled")
    else:
        rows = transcript_lines(source)
    if not rows:
        raise SystemExit(f"no transcript lines in {source}")
    out.mkdir(parents=True)  # refuses an existing folder
    (out / "lines.json").write_text(json.dumps([f"[{s}] {n}: {t}" for s, n, t in rows], ensure_ascii=False, indent=1))
    (out / "transcript.md").write_text(f"# Transcript ({source if source.startswith('script') else 'pipeline'})\n\n"
                                       + "\n\n".join(f"**[{s}] {n}:** {t}" for s, n, t in rows) + "\n")
    if source == "script-relabeled":
        (out / "names.json").write_text(json.dumps({f"Speaker {v}": k for k, v in ROTATION.items()}, indent=1))
    subprocess.run(["uv", "run", "--project", str(PIPELINE), "python", str(PIPELINE / "summary_stage.py"),
                    str(out / "lines.json"), str(out / "raw.json"), variant], check=True,
                   env={**os.environ, "HF_HUB_OFFLINE": "1"})
    raw = json.loads((out / "raw.json").read_text())
    reply = re.sub(r"<think>.*?</think>", "", raw["replies"][-1]["reply"], flags=re.S)
    notes = json.loads(reply[reply.find("{"):reply.rfind("}") + 1])
    summary = {k: raw[k] for k in ("model", "model_revision", "decoding", "thinking", "variant", "chunks",
                                   "mlx_peak_bytes")}
    summary.update(notes={k: [i for i in notes.get(k) or [] if isinstance(i, dict)] for k in SECTIONS},
                   seconds=sum(r["seconds"] for r in raw["replies"]),
                   replies=[{"kind": r["kind"], "prompt_tokens": r["prompt_tokens"], "seconds": r["seconds"],
                             "reply": r["reply"]} for r in raw["replies"]])
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    (out / "raw.json").unlink()
    (out / "lines.json").unlink()
    print(f"{out.name}: {summary['seconds']:.0f} s")


if __name__ == "__main__":
    main(*sys.argv[1:4])
