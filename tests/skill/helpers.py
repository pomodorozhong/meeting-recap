"""Shared fixtures: a throwaway dataset outside any Git checkout, built from generated audio."""
import json
import math
import random
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / ".agents" / "skills" / "meeting-experiment-review"
SCRIPTS = SKILL / "scripts"
# Load the standard modules the server needs before the scripts folder joins sys.path, so a
# script that shadows one (select.py did) fails the shadowing and CLI tests instead of hanging
# the in-process server tests.
import http.server  # noqa: E402,F401
import selectors  # noqa: E402,F401
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import dataset as dataset_cli  # noqa: E402


def write_wav(path, seconds, rate=8000):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(struct.pack("<h", 0) * int(seconds * rate))
    return path


def write_track(path, seconds, bursts, rate=8000, amplitude=8000, noise=30, seed=0):
    """A generated speaker track: low noise, plus a 300 Hz tone for each (start, end[, amplitude]) burst."""
    rng = random.Random(seed)
    samples = [rng.randint(-noise, noise) for _ in range(int(seconds * rate))]
    for start, end, *level in bursts:
        for i in range(int(start * rate), int(end * rate)):
            samples[i] += int((level[0] if level else amplitude) * math.sin(2 * math.pi * 300 * i / rate))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def segs(*rows):
    """segs(("A", 0, 5), ("B", 5, 9)) -> segments artifact."""
    return [{"speaker_id": s, "start_seconds": a, "end_seconds": b} for s, a, b in rows]


def transcript(*words):
    """transcript(("你", 0, 1), ...) -> WhisperKit-shaped JSON with one segment per word."""
    return {"text": "".join(w for w, _, _ in words),
            "segments": [{"start": a, "end": b, "text": w, "words": [{"word": w, "start": a, "end": b}]}
                         for w, a, b in words]}


class DatasetCase(unittest.TestCase):
    """Each test gets a fresh dataset in a temporary directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        dataset_cli.init(self.tmp / "ds")
        self.root = common.dataset(self.tmp / "ds")

    def tearDown(self):
        self._tmp.cleanup()

    def add_recording(self, recording_id="rec1", seconds=60.0, group=None):
        audio = write_wav(self.tmp / "in" / f"{recording_id}.wav", seconds)
        return dataset_cli.add_recording(self.root, recording_id, audio, seconds, group)

    def add_run(self, run_id, recording_id="rec1", artifacts=None, status="completed", model="test-model"):
        spec_dir = self.tmp / "specs" / run_id
        files = {name: write_json(spec_dir / f"{name}.json", data).name for name, data in (artifacts or {}).items()}
        spec = write_json(spec_dir / "run.json", {"id": run_id, "recording_id": recording_id, "model": model,
                                                  "status": status, "artifacts": files})
        return dataset_cli.add_run(self.root, spec)
