#!/usr/bin/env python3
"""Recap the synthetic call's own script, with true text and speakers, through the pipeline's summary stage.

usage: script_recap.py OUT_DIR

This is the recap with no ASR or diarization errors: whatever it gets wrong is the summary model's own
error. It writes OUT_DIR/transcript.md in the pipeline's format, then runs the pipeline's summary_stage.py
as a command (nothing is imported across experiment folders) and adds the parsed notes to summary.json.
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


def stamp(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def main(out):
    out = Path(out)
    out.mkdir(parents=True)  # refuses an existing folder
    turns = json.loads(REFERENCE.read_text())["segments"]
    lines = [f"[{stamp(t['start'])}] Speaker {t['speaker']}: {t['text']}" for t in turns]
    (out / "lines.json").write_text(json.dumps(lines, ensure_ascii=False, indent=1))
    (out / "transcript.md").write_text("# Transcript (script)\n\n" + "\n\n".join(
        f"**[{stamp(t['start'])}] Speaker {t['speaker']}:** {t['text']}" for t in turns) + "\n")
    subprocess.run(["uv", "run", "--project", str(PIPELINE), "python", str(PIPELINE / "summary_stage.py"),
                    str(out / "lines.json"), str(out / "raw.json")], check=True,
                   env={**os.environ, "HF_HUB_OFFLINE": "1"})
    raw = json.loads((out / "raw.json").read_text())
    reply = re.sub(r"<think>.*?</think>", "", raw["replies"][-1]["reply"], flags=re.S)
    notes = json.loads(reply[reply.find("{"):reply.rfind("}") + 1])
    raw["notes"] = {k: [i for i in notes.get(k) or [] if isinstance(i, dict)] for k in SECTIONS}
    (out / "summary.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1))
    (out / "raw.json").unlink()
    print(f"wrote {out / 'summary.json'}")


if __name__ == "__main__":
    main(sys.argv[1])
