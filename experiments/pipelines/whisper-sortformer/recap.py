#!/usr/bin/env python3
"""Saved recording -> speaker-labeled Traditional Chinese Markdown transcript -> local recap.

  setup                      download the pinned models (needs the network once)
  run AUDIO OUT [--resume]   run every stage into a new output folder, offline
  render OUT                 rebuild transcript.md after editing OUT/speakers.json
  summarize OUT [--replace]  rerun the recap with the current speaker names
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time

import pins
import pipeline

HERE = Path(__file__).resolve().parent
STAGES = ("convert", "asr", "diarize", "attach", "transcript", "summary")


class StageError(Exception):
    pass


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_atomic(path, content):
    """Write text or JSON beside its destination, then rename, so a crash never leaves half a file."""
    path = Path(path)
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=1) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.",
                                     delete=False) as handle:
        handle.write(text)
    os.replace(handle.name, path)


def git_commit():
    try:
        commit = subprocess.run(["git", "-C", str(HERE), "rev-parse", "HEAD"], capture_output=True, text=True,
                                check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(HERE), "status", "--porcelain", "--", "."], capture_output=True,
                               text=True, check=True).stdout.strip()
        return commit + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def parse_time(path):
    """Wall time, peak RSS and peak memory footprint from `/usr/bin/time -l -o`."""
    text = Path(path).read_text()
    found = {}
    for key, pattern in (("wall_seconds", r"([\d.]+) real"), ("max_rss_bytes", r"(\d+)\s+maximum resident set size"),
                         ("peak_footprint_bytes", r"(\d+)\s+peak memory footprint")):
        match = re.search(pattern, text)
        if match:
            found[key] = float(match.group(1)) if key == "wall_seconds" else int(match.group(1))
    return found


def measured(out, name, argv, env=None):
    """Run one stage's process under /usr/bin/time -l; its output goes to logs/<name>.log."""
    logs = out / "logs"
    logs.mkdir(exist_ok=True)
    log, timing = logs / f"{name}.log", logs / f"{name}.time"
    with open(log, "w") as handle:
        code = subprocess.run(["/usr/bin/time", "-l", "-o", str(timing), *argv], stdout=handle,
                              stderr=subprocess.STDOUT, env=env, cwd=HERE).returncode
    stats = parse_time(timing) if timing.exists() else {}
    if code != 0:
        tail = log.read_text(errors="replace").strip().splitlines()[-5:]
        raise StageError(f"exited with code {code}; last lines of logs/{name}.log:\n  " + "\n  ".join(tail))
    return stats


def python_stage(out, name, script, *args):
    env = {**os.environ, "HF_HUB_OFFLINE": "1", "PYTHONUNBUFFERED": "1"}
    return measured(out, name, [sys.executable, str(HERE / script), *map(str, args)], env)


class Run:
    """One output folder: its manifest (run.json) and stage records (stages.json)."""

    def __init__(self, out):
        self.out = Path(out)
        self.stages_path = self.out / "stages.json"
        self.stages = read_json(self.stages_path) if self.stages_path.exists() else {}

    def done(self, name):
        record = self.stages.get(name, {})
        return record.get("status") == "completed" and all(
            (self.out / f).exists() and sha256(self.out / f) == digest for f, digest in record["outputs"].items())

    def stage(self, name, action, outputs):
        """Run `action()` and record its status, timing and output digests; a failure keeps earlier outputs."""
        record = {"status": "running", "started_at": now()}
        self.stages[name] = record
        write_atomic(self.stages_path, self.stages)
        print(f"[{name}] started", flush=True)
        started = time.monotonic()
        try:
            stats = action() or {}
            missing = [f for f in outputs if not (self.out / f).exists()]
            if missing:
                raise StageError(f"did not write {', '.join(missing)}")
        except Exception as error:  # any failure is recorded against this stage before it is reported
            record.update(status="failed", seconds=round(time.monotonic() - started, 2),
                          error=f"{type(error).__name__}: {error}")
            write_atomic(self.stages_path, self.stages)
            raise StageError(f"stage {name} failed: {error}") from None
        record.update(status="completed", seconds=round(time.monotonic() - started, 2), **stats,
                      outputs={f: sha256(self.out / f) for f in outputs})
        write_atomic(self.stages_path, self.stages)
        print(f"[{name}] completed in {record['seconds']:.1f} s", flush=True)


def prepare(audio, out, resume):
    audio, out = Path(audio).resolve(), Path(out).resolve()
    if not audio.is_file():
        raise ValueError(f"{audio} is not a file")
    if HERE.parents[2] in out.parents or out == HERE.parents[2]:
        raise ValueError("the output folder must be outside the Git checkout; recordings and transcripts stay private")
    digest = sha256(audio)
    if out.exists() and any(out.iterdir()):
        if not resume:
            raise ValueError(f"{out} already exists and is not empty; choose a new folder, or pass --resume "
                             "to continue the run in it")
        manifest = read_json(out / "run.json")
        if manifest["input_sha256"] != digest:
            raise ValueError(f"{out} holds a run of a different recording; choose a new folder")
        return audio, out
    if resume:
        raise ValueError(f"{out} has no run to resume")
    out.mkdir(parents=True, exist_ok=True)
    write_atomic(out / "run.json", {
        "pipeline": "whisper-sortformer", "code_commit": git_commit(), "created_at": now(),
        "input_name": audio.name, "input_sha256": digest,
        "models": {"asr": f"{pins.WHISPER_REPO}@{pins.WHISPER_REVISION}",
                   "diarization": f"FluidAudio Sortformer, fluidaudiocli@{pins.FLUIDAUDIO_REVISION}",
                   "summary": f"{pins.SUMMARY_REPO}@{pins.SUMMARY_REVISION}"},
        "machine": {"platform": platform.platform(), "processor": platform.processor()}})
    return audio, out


def convert(audio, out):
    partial = out / ".audio.partial.wav"
    stats = measured(out, "convert", ["ffmpeg", "-nostdin", "-y", "-i", str(audio), "-ac", "1", "-ar", "16000",
                                      "-c:a", "pcm_f32le", str(partial)])
    os.replace(partial, out / "audio.wav")
    return stats


def duration(out):
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            str(out / "audio.wav")], capture_output=True, text=True, check=True)
    return float(probe.stdout.strip())


def asr(out):
    partial = out / ".asr.partial.json"
    stats = python_stage(out, "asr", "asr_stage.py", out / "audio.wav", partial)
    data = read_json(partial)
    stats["mlx_peak_bytes"] = data["mlx_peak_bytes"]
    os.replace(partial, out / "asr.json")
    return stats


def diarize(out):
    if not pins.FLUIDAUDIO_CLI.exists():
        raise StageError(f"{pins.FLUIDAUDIO_CLI.name} is not built; run `swift build -c release --product "
                         "fluidaudiocli` in the pipeline folder")
    raw = out / "sortformer.raw.json"
    raw.unlink(missing_ok=True)
    stats = measured(out, "diarize", [str(pins.FLUIDAUDIO_CLI), "sortformer", str(out / "audio.wav"),
                                      "--output", str(raw)])
    # fluidaudiocli exits 0 even when it fails, so its output file is the only success signal.
    if not raw.exists():
        tail = (out / "logs/diarize.log").read_text(errors="replace").strip().splitlines()[-3:]
        raise StageError("Sortformer wrote no output; last lines of logs/diarize.log:\n  " + "\n  ".join(tail))
    write_atomic(out / "diarization.json", pipeline.sortformer_segments(read_json(raw)))
    return stats


def attach(out):
    turns = pipeline.attach(read_json(out / "asr.json"), read_json(out / "diarization.json"))
    write_atomic(out / "turns.json", turns)
    if not (out / "speakers.json").exists():  # never replace names the user already edited
        write_atomic(out / "speakers.json", pipeline.default_speakers(turns))


def named(out):
    turns = read_json(out / "turns.json")
    labels = pipeline.check_speakers(read_json(out / "speakers.json"), turns)
    from opencc import OpenCC

    convert = OpenCC("s2tw").convert
    return pipeline.named_turns(turns, labels, convert)


def transcript(out):
    write_atomic(out / "transcript.md", pipeline.transcript_markdown(named(out), duration(out)))


def summary(out, replace=False):
    if not replace and (out / "summary.md").exists():
        raise StageError("summary.md already exists; pass --replace to write a new one")
    lines = pipeline.transcript_lines(named(out))
    if not lines:
        raise StageError("the transcript is empty; there is nothing to summarize")
    write_atomic(out / ".summary-input.json", lines)
    partial = out / ".summary.partial.json"
    stats = python_stage(out, "summary", "summary_stage.py", out / ".summary-input.json", partial)
    raw = read_json(partial)
    notes = pipeline.parse_notes(raw["replies"][-1]["reply"])
    raw["checks"] = pipeline.check_evidence(notes, lines)
    raw["notes"] = notes
    raw["speakers_sha256"] = sha256(out / "speakers.json")
    stats["mlx_peak_bytes"] = raw["mlx_peak_bytes"]
    write_atomic(out / "summary.json", raw)
    write_atomic(out / "summary.md", pipeline.summary_markdown(notes))
    partial.unlink()
    (out / ".summary-input.json").unlink()
    return stats


def run(args):
    audio, out = prepare(args.audio, args.out, args.resume)
    record = Run(out)
    plan = [("convert", lambda: convert(audio, out), ["audio.wav"]),
            ("asr", lambda: asr(out), ["asr.json"]),
            ("diarize", lambda: diarize(out), ["sortformer.raw.json", "diarization.json"]),
            ("attach", lambda: attach(out), ["turns.json", "speakers.json"]),
            ("transcript", lambda: transcript(out), ["transcript.md"])]
    if not args.no_summary:
        plan.append(("summary", lambda: summary(out, replace=record.stages.get("summary", {}).get("status")
                                                != "completed"), ["summary.json", "summary.md"]))
    started = time.monotonic()
    for name, action, outputs in plan:
        if args.resume and record.done(name):
            print(f"[{name}] already completed; kept", flush=True)
            continue
        record.stage(name, action, outputs)
    record.stages["total"] = {"seconds": round(time.monotonic() - started, 2),
                              "note": "this invocation only; stages skipped by --resume add nothing"}
    write_atomic(record.stages_path, record.stages)
    print(f"done: {out / 'transcript.md'}" + ("" if args.no_summary else f" and {out / 'summary.md'}"))


def render(args):
    out = Path(args.out).resolve()
    Run(out).stage("transcript", lambda: transcript(out), ["transcript.md"])
    summary_path = out / "summary.json"
    if summary_path.exists() and read_json(summary_path).get("speakers_sha256") != sha256(out / "speakers.json"):
        print("note: summary.md used earlier speaker names; run `summarize --replace` to update it")


def summarize(args):
    out = Path(args.out).resolve()
    if not args.replace and (out / "summary.md").exists():
        # Refuse before recording the stage, so the existing summary keeps its completed record.
        raise ValueError("summary.md already exists; pass --replace to write a new one")
    Run(out).stage("summary", lambda: summary(out, replace=True), ["summary.json", "summary.md"])


def setup(_args):
    for repo, revision in ((pins.WHISPER_REPO, pins.WHISPER_REVISION), (pins.SUMMARY_REPO, pins.SUMMARY_REVISION)):
        print(f"{repo}@{revision}: {pins.snapshot(repo, revision)}")
    if not pins.FLUIDAUDIO_CLI.exists():
        raise ValueError("build the diarizer first: swift build -c release --product fluidaudiocli")
    with tempfile.TemporaryDirectory() as directory:
        wav, result = Path(directory) / "silence.wav", Path(directory) / "out.json"
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                        "-t", "3", str(wav)], check=True)
        # The first Sortformer run downloads FluidAudio's models.
        subprocess.run([str(pins.FLUIDAUDIO_CLI), "sortformer", str(wav), "--output", str(result)],
                       capture_output=True, check=True)
        if not result.exists():
            raise ValueError("Sortformer could not run; check the network and FluidAudio's model download")
    print("setup complete; `run` now works offline")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup", help="download pinned models").set_defaults(func=setup)
    p = commands.add_parser("run", help="run every stage")
    p.add_argument("audio")
    p.add_argument("out", help="a new folder outside the Git checkout")
    p.add_argument("--resume", action="store_true", help="continue a failed or partial run in OUT")
    p.add_argument("--no-summary", action="store_true", help="stop after the transcript")
    p.set_defaults(func=run)
    p = commands.add_parser("render", help="rebuild transcript.md from speakers.json")
    p.add_argument("out")
    p.set_defaults(func=render)
    p = commands.add_parser("summarize", help="rerun the recap")
    p.add_argument("out")
    p.add_argument("--replace", action="store_true", help="replace an existing summary.md")
    p.set_defaults(func=summarize)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (StageError, ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        if getattr(args, "out", None):
            print(f"completed outputs are kept in {args.out}; see stages.json and logs/", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
