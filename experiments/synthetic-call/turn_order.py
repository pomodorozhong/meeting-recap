"""Evaluate both raw diarizers and 12 attachments through the review skill on one synthetic case."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SKILL = HERE.parents[1] / ".agents/skills/meeting-experiment-review/scripts"


def load(path):
    return json.loads(path.read_text())


def run(source, result, dataset):
    case = result.name
    manifest = load(source / "manifest.json")
    if hashlib.sha256((source / "call.wav").read_bytes()).hexdigest() != manifest["call_sha256"]:
        raise ValueError("recording digest mismatch")
    if manifest["call_sha256"] != (result / "input.sha256").read_text().strip():
        raise ValueError("results belong to a different recording")
    # The skill enforces the outside-Git boundary. A new dataset keeps reruns independent.
    if dataset.exists():
        raise FileExistsError(f"use a new dataset directory: {dataset}")

    def cli(tool, command, *args):
        argv = [sys.executable, SKILL / (tool + ".py")]
        if command:
            argv.append(command)
        argv.extend([dataset, *args])
        proc = subprocess.run(argv, text=True, capture_output=True)
        if proc.returncode:
            raise ValueError(proc.stderr.strip() or f"{tool} exited {proc.returncode}")
        return json.loads(proc.stdout)

    cli("dataset", "init")
    cli("dataset", "add-recording", "--id", case, "--audio", source / "call.wav",
        "--duration", str(manifest["duration_seconds"]), "--group", "synthetic")
    reference = f"ref-{case}"
    cli("review", "known", "--recording", case, "--segments", source / "segments.json", "--id", reference)
    pipe = result / "pipeline"
    pipeline_run = load(pipe / "run.json")
    errors = {}
    parents = {}
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        who = load(result / "who.json")
        who_segments = scratch / "who-segments.json"
        who_segments.write_text(json.dumps(who["segments"]))
        breeze = load(result / "breeze.json")
        for name, kind, file, config in (
            ("whisper", "transcript", pipe / "asr.json", pipeline_run["models"]["asr"]),
            ("breeze", "transcript", result / "breeze.json", breeze["model_revision"]),
            ("sortformer", "segments", pipe / "diarization.json", pipeline_run["models"]["diarization_weights_sha256"]),
            ("who", "segments", who_segments, who["model_revision"]),
        ):
            rid = f"{case}-{name}"
            spec = {"id": rid, "model": name, "status": "completed", "recording_id": case,
                    "config": {"pin": config}, "artifacts": {kind: str(file.resolve())}}
            path = scratch / "spec.json"
            path.write_text(json.dumps(spec))
            try:
                cli("dataset", "add-run", "--spec", path)
                parents[name] = rid
            except ValueError as error:
                errors[rid] = str(error)
    runs = [parents[d] for d in ("sortformer", "who") if d in parents]
    for asr in ("whisper", "breeze"):
        for diarizer in ("sortformer", "who"):
            if asr not in parents or diarizer not in parents:
                continue
            for method in ("word", "seg", "line"):
                rid = f"{case}-{asr}-{diarizer}-{method}"
                try:
                    cli("attach", None, "--asr-run", parents[asr], "--diarization-run", parents[diarizer],
                        "--id", rid, "--method", method)
                    runs.append(rid)
                except ValueError as error:
                    errors[rid] = str(error)
    evaluation = cli("evaluate", None, "--reference", reference, "--runs", *runs, "--id", f"eval-{case}")
    cli("dataset", "validate")
    return {"recording": case, "code": evaluation["code"]["sha256"], "excluded": len(evaluation["excluded"]),
            "errors": errors, "results": {row["run_id"]: {k: row[k] for k in
                ("reference_turns", "turns_recovered", "clips", "clips_correct")} for row in evaluation["results"]}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "result", "new_dataset"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.source.resolve(), args.result.resolve(), args.new_dataset.resolve()), indent=2))
