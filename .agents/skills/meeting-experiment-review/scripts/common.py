"""Private dataset IO shared by the standalone skill helpers (standard library only)."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

FORMAT = "meeting-review-dataset"
VERSION = 1


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value):
        raise ValueError("IDs must contain 1–64 letters, digits, underscores, or hyphens")
    return value


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid number: {value}")))


def write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(",", ":")).encode()).hexdigest()


SKILL_DIR = Path(__file__).resolve().parent.parent


def code_files(skill_dir=SKILL_DIR):
    files = sorted(p for p in (skill_dir / "scripts").glob("*.py"))
    return [*files, skill_dir / "assets" / "review.html"]


def snapshot(root):
    """Copy the running skill code into <dataset>/code/<sha256>/ once, and return a record of it.

    Experiments keep using the exact code that produced them even after the skill changes:
    rerun a step with python3 <dataset>/code/<sha256>/scripts/<script>.py.
    """
    import shutil
    import subprocess
    import tempfile
    files = {str(p.relative_to(SKILL_DIR)): digest(p) for p in code_files()}
    code_id = fingerprint(files)
    target = private(root, root / "code") / code_id
    if not target.exists():
        # Each caller stages its own copy; the first rename publishes it, and later callers reuse that one.
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{code_id}.", suffix=".tmp", dir=target.parent))
        try:
            for name in files:
                (staging / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(SKILL_DIR / name, staging / name)
            git = {}
            try:
                run_git = lambda *args: subprocess.run(["git", "-C", str(SKILL_DIR), *args], capture_output=True,
                                                       text=True, check=True).stdout.strip()
                git = {"commit": run_git("rev-parse", "HEAD"), "dirty": bool(run_git("status", "--porcelain", "--", "."))}
            except (OSError, subprocess.CalledProcessError):
                pass
            write_new(staging / "code.json", {"sha256": code_id, "files": files, "git": git, "created_at": now()})
            try:
                staging.rename(target)
            except OSError:
                if not (target / "code.json").exists():
                    raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    info = read_json(target / "code.json")
    if info["files"] != files:
        raise ValueError(f"code snapshot {code_id} does not match the running code")
    return {"sha256": code_id, "git": info["git"]}


def number(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be a finite number >= {minimum}")
    return value


def span(start, end):
    number(start, "start_seconds")
    number(end, "end_seconds")
    if end <= start:
        raise ValueError("end_seconds must be after start_seconds")


def inside(root, relative):
    root = Path(root).resolve()
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError("dataset artifact paths must be relative")
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError("artifact path escapes the dataset")
    return target


def outside_git(path):
    """Resolve a private destination, refusing one inside a Git checkout (a worktree's .git is a file)."""
    path = Path(path).expanduser().resolve()
    if any((parent / ".git").exists() for parent in (path, *path.parents)):
        raise ValueError(f"keep private data outside any Git checkout: {path} is inside one")
    return path


def private(root, path):
    """Resolve a write destination, refusing one that a symlink takes out of the dataset or into a Git checkout."""
    target = Path(path).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"{Path(path).relative_to(root)} leads outside the dataset; replace the symlink with a folder")
    return outside_git(target)


def dataset(path, write=True):
    """Open a dataset; only read-only commands such as validate pass write=False to open one inside a checkout."""
    root = Path(path).expanduser().resolve()
    info = read_json(root / "dataset.json")
    if info.get("format") != FORMAT or info.get("version") != VERSION:
        raise ValueError("unsupported review dataset")
    return outside_git(root) if write else root


def recording(root, recording_id):
    info = read_json(root / "recordings" / identifier(recording_id) / "recording.json")
    inside(root, info["media"])
    return info


def run(root, run_id):
    return read_json(root / "runs" / identifier(run_id) / "run.json")


def artifact(root, info, name):
    """Read a run's artifact after checking it against the digest recorded when it was registered."""
    entry = info["artifacts"].get(name)
    if entry is None:
        raise ValueError(f"run {info['id']} has no {name} artifact")
    path = inside(root, entry["path"])
    if digest(path) != entry["sha256"]:
        raise ValueError(f"run {info['id']}: {name} artifact changed since registration")
    return read_json(path)


def session(root, session_id):
    return read_json(root / "sessions" / identifier(session_id) / "session.json")


def events(root, session_id):
    path = root / "sessions" / identifier(session_id) / "events.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if [row["seq"] for row in rows] != list(range(1, len(rows) + 1)):
        raise ValueError("review event sequence has a gap")
    return rows


def append_event(root, session_id, event, expected_revision=None):
    # A file lock also serializes writes from the server and CLI. The app is local-only.
    import fcntl
    directory = private(root, root / "sessions" / identifier(session_id))
    # The files themselves could be symlinks too, so check where each one really leads before opening it.
    log, lock_path = (private(root, directory / name) for name in ("events.jsonl", ".lock"))
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = events(root, session_id)
        if expected_revision is not None and expected_revision != len(rows):
            raise ValueError("review changed; reload before saving this answer")
        row = {**event, "seq": len(rows) + 1, "at": now()}
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        return row


def answers(root, session_id, until=None, rows=None):
    """Latest answer per item; pass `rows` from one events() read so answers and revision agree."""
    rows = events(root, session_id) if rows is None else rows
    return {event["item_id"]: event for event in rows
            if event["type"] == "answer" and (until is None or event["seq"] <= until)}


def segments(data):
    if not isinstance(data, list):
        raise ValueError("segments must be an array")
    for item in data:
        span(item["start_seconds"], item["end_seconds"])
        if not isinstance(item["speaker_id"], str) or not item["speaker_id"]:
            raise ValueError("segment speaker_id must be a nonempty string")
    return data
