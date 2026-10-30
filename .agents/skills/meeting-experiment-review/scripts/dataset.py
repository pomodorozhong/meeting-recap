#!/usr/bin/env python3
"""Create private datasets and register immutable recording/run artifacts."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from common import (FORMAT, VERSION, dataset, digest, identifier, inside, now, number,
                    read_json, recording, segments, write_new)


def init(path):
    root = Path(path).expanduser().resolve()
    if any((parent / ".git").exists() for parent in (root, *root.parents)):
        raise ValueError("create the private dataset outside any Git checkout")
    if root.exists() and any(root.iterdir()):
        raise ValueError("dataset destination must be empty or new")
    write_new(root / "dataset.json", {"format": FORMAT, "version": VERSION, "created_at": now()})
    return {"dataset": str(root)}


def add_recording(root, recording_id, audio, duration, group=None):
    identifier(recording_id)
    number(duration, "duration_seconds", minimum=0.001)
    audio = Path(audio).expanduser().resolve(strict=True)
    directory = root / "recordings" / recording_id
    if directory.exists():
        raise ValueError("recording ID already exists")
    extension = audio.suffix.lower()
    if extension not in {".wav", ".mp3", ".mp4", ".m4a", ".flac", ".ogg", ".webm", ".aiff", ".aac"}:
        raise ValueError("unsupported media extension")
    directory.mkdir(parents=True)
    target = directory / ("source" + extension)
    try:
        shutil.copyfile(audio, target)
        info = {"id": recording_id, "sha256": digest(target), "duration_seconds": duration,
                "group": identifier(group or recording_id), "media": str(target.relative_to(root))}
        write_new(directory / "recording.json", info)
    except Exception:
        shutil.rmtree(directory)
        raise
    return info


def add_run(root, spec_path):
    spec_path = Path(spec_path).resolve()
    spec = read_json(spec_path)
    run_id = identifier(spec["id"])
    recording(root, spec["recording_id"])
    if spec.get("status") not in {"completed", "failed", "incomplete"}:
        raise ValueError("run status must be completed, failed, or incomplete")
    if not isinstance(spec.get("model"), str) or not spec["model"]:
        raise ValueError("run model is required")
    sources = {}
    for name, source in spec.get("artifacts", {}).items():
        identifier(name)
        path = (spec_path.parent / source).resolve(strict=True)
        if name == "segments":
            segments(read_json(path))
        sources[name] = path
    directory = root / "runs" / run_id
    if directory.exists():
        raise ValueError("run ID already exists; register a new run instead of replacing predictions")
    directory.mkdir(parents=True)
    artifacts = {}
    try:
        for name, source in sources.items():
            # Names do not inherit user filenames or their directory layout.
            target = directory / (name + source.suffix)
            shutil.copyfile(source, target)
            artifacts[name] = {"path": str(target.relative_to(root)), "sha256": digest(target)}
        info = {"id": run_id, "recording_id": spec["recording_id"], "created_at": now(),
                "model": spec["model"], "status": spec["status"], "artifacts": artifacts,
                "config": spec.get("config", {}), "runtime": spec.get("runtime", {}),
                "notes": spec.get("notes", "")}
        write_new(directory / "run.json", info)
    except Exception:
        shutil.rmtree(directory)
        raise
    return info


def validate(root):
    counts = {"recordings": 0, "runs": 0, "sessions": 0, "references": 0, "code": 0}
    for path in (root / "recordings").glob("*/recording.json"):
        item = read_json(path)
        if digest(inside(root, item["media"])) != item["sha256"]:
            raise ValueError(f"recording changed: {item['id']}")
        counts["recordings"] += 1
    for path in (root / "runs").glob("*/run.json"):
        item = read_json(path)
        recording(root, item["recording_id"])
        for artifact in item["artifacts"].values():
            if digest(inside(root, artifact["path"])) != artifact["sha256"]:
                raise ValueError(f"run artifact changed: {item['id']}")
        counts["runs"] += 1
    from common import fingerprint as code_fingerprint
    for path in (root / "code").glob("*/code.json"):
        if path.parent.name.startswith("."):
            continue  # a snapshot still being staged, or one abandoned by a crash
        item = read_json(path)
        files = {name: digest(inside(path.parent, name)) for name in item["files"]}
        if files != item["files"] or code_fingerprint(files) != item["sha256"] or item["sha256"] != path.parent.name:
            raise ValueError(f"code snapshot changed: {path.parent.name}")
        counts["code"] += 1
    from review import validate_plan
    from common import events
    for path in (root / "sessions").glob("*/session.json"):
        item = read_json(path)
        validate_plan(root, item)
        events(root, item["id"])
        counts["sessions"] += 1
    from common import fingerprint
    for path in (root / "references").glob("*.json"):
        item = read_json(path)
        expected = item.pop("sha256")
        if fingerprint(item) != expected:
            raise ValueError("reference snapshot changed")
        counts["references"] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("init")
    create.add_argument("dataset")
    add = sub.add_parser("add-recording")
    add.add_argument("dataset")
    add.add_argument("--id", required=True)
    add.add_argument("--audio", required=True)
    add.add_argument("--duration", type=float, required=True, help="seconds; inspect with ffprobe")
    add.add_argument("--group", help="same call's parts share a group for future evaluation splits")
    run = sub.add_parser("add-run")
    run.add_argument("dataset")
    run.add_argument("--spec", required=True)
    check = sub.add_parser("validate")
    check.add_argument("dataset")
    freeze = sub.add_parser("snapshot", help="copy the current skill code into the dataset and print its ID")
    freeze.add_argument("dataset")
    args = parser.parse_args()
    if args.command == "init":
        result = init(args.dataset)
    else:
        root = dataset(args.dataset)
        if args.command == "add-recording":
            result = add_recording(root, args.id, args.audio, args.duration, args.group)
        elif args.command == "add-run":
            result = add_run(root, args.spec)
        elif args.command == "snapshot":
            from common import snapshot
            result = snapshot(root)
        else:
            result = validate(root)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        sys.exit(str(error))
