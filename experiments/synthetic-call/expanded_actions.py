"""Replay the historical action prompts on two expanded-corpus scripts, without giving them the keys."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib

from collection import HERE, build, digest, load
from expanded_followup import PIPE, save

HISTORY = "c714e0535411e04ec291172e0a7e70c44443df15"
# Execute the frozen extractor in its own source tree and its original locked pipeline runtime.
EXTRACT = """
import json, sys
from pathlib import Path
import action_bench as a
lines, output, mode, python, candidates = json.load(sys.stdin)
stats = a.extract(lines, Path(output), mode, Path(python), Path(candidates) if candidates else None)
a.write(Path(output) / 'run.json', stats)
"""
REPAIR = """
import json, sys
from action_bench import relabel_lines
print(json.dumps(relabel_lines(*json.load(sys.stdin))))
"""
RENDER = """
import json, sys
from pathlib import Path
import recap
out = Path(sys.argv[1])
recap.attach(out)
named = recap.named(out)
print(json.dumps({'lines':recap.pipeline.transcript_lines(named),'turns':named}))
"""
MAP = """
import json, sys
from action_bench import speaker_map
print(json.dumps(speaker_map(*json.load(sys.stdin))))
"""


def historical_source(folder):
    for group, files in (("synthetic-call", ("action_bench.py", "collection.py", "score_case.py", "score_speakers.py")),
                         ("pipelines/whisper-sortformer", ("summary_stage.py", "pipeline.py", "pins.py",
                                                           "model_sources.json", "Package.resolved", "uv.lock"))):
        for name in files:
            path = Path("experiments") / group / name
            dest = folder / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(subprocess.check_output(["git", "show", f"{HISTORY}:{path}"], cwd=HERE))
    def resolution(lock):
        return [p for p in tomllib.loads(lock.read_text())["package"] if "virtual" not in p["source"]]
    if resolution(folder / "experiments/pipelines/whisper-sortformer/uv.lock") != resolution(PIPE / "uv.lock"):
        raise ValueError("historical action runner requires its own locked pipeline environment")


def run(fixtures, results):
    if any((p / ".git").exists() for p in [results, *results.parents]):
        raise ValueError("results must be outside Git")
    build(fixtures, check_only=True)
    with tempfile.TemporaryDirectory() as tmp:
        historical_source(Path(tmp))
        older = Path(tmp) / "experiments/synthetic-call"
        def old(command, args):
            return subprocess.check_output([sys.executable, "-c", command], cwd=older,
                                           input=json.dumps(args), text=True, env={**os.environ, "HF_HUB_OFFLINE":"1"})

        for name in ("scheduling", "localization"):
            src, case = fixtures / name, results / name
            if (case / "input.sha256").read_text().strip() != digest(src / "call.wav"):
                raise ValueError("wrong input audio")
            target = case / "actions"
            target.mkdir()
            known = load(src / "segments.json")
            exact = []
            for turn in load(src / "transcript.json")["segments"]:
                sec = int(turn["start"])
                exact.append(f"[{sec//3600:02}:{sec//60%60:02}:{sec%60:02}] Speaker {turn['speaker']}: {turn['text']}")
            lines = {"exact": exact}
            for model in ("turbo", "whisper"):
                folder = target / model
                folder.mkdir()
                (folder / "asr.json").symlink_to(case / f"{model}.json")
                (folder / "diarization.json").symlink_to(case / "sortformer.json")
                data = json.loads(subprocess.check_output([PIPE / ".venv/bin/python", "-c", RENDER, folder], cwd=PIPE))
                labels = load(folder / "speakers.json")["labels"]
                save(folder / "mapping.json", json.loads(old(MAP, [known, load(case / "sortformer.json"), labels])))
                lines[model] = data["lines"]
                if model == "turbo":
                    lines["repaired"] = json.loads(old(REPAIR, [data["lines"], data["turns"], known]))

            for source, mode in (("exact","ordinary"), ("exact","focused"), ("turbo","ordinary"),
                                 ("turbo","focused"), ("whisper","focused"), ("repaired","focused"), ("turbo","verify")):
                print(name, source, mode, flush=True)
                candidates = target / "turbo-focused/items.json" if mode == "verify" else None
                old(EXTRACT, [lines[source], str(target / f"{source}-{mode}"), mode,
                              str(PIPE / ".venv/bin/python"), str(candidates) if candidates else None])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("fixtures", type=Path)
    p.add_argument("results", type=Path)
    args = p.parse_args()
    run(args.fixtures.resolve(), args.results.resolve())
