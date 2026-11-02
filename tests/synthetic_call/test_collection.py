"""Exercise the collection's audio controls and safe verification without running TTS."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
import collection as c


def source(root, name):
    folder = root / name
    folder.mkdir()
    data = np.zeros(3 * c.RATE)
    turns = [("A", 0.5, 1.5, 0.1), ("B", 1.8, 2.8, 0.2)]
    for _, start, end, level in turns:
        data[round(start * c.RATE):round(end * c.RATE)] = level
    sf.write(folder / "call.wav", data, c.RATE, subtype="PCM_16")
    (folder / "segments.json").write_text(json.dumps([
        {"speaker_id": who, "start_seconds": a, "end_seconds": b} for who, a, b, _ in turns]))
    (folder / "transcript.json").write_text(json.dumps({"segments": [
        {"speaker": who, "text": who, "start": a, "end": b} for who, a, b, _ in turns]}))


class RecordingControls(unittest.TestCase):
    def test_channel_attenuates_b_preserves_timing_and_repeats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source(root, "handoff")
            for path in (root / "first", root / "second"):
                c.write_control(root, "handoff-channel", path)
            audio, rate = sf.read(root / "first/call.wav")
            self.assertAlmostEqual(audio[rate:rate + 1000].mean(), 0.1, delta=0.002)
            self.assertAlmostEqual(audio[2*rate:2*rate + 1000].mean(), 0.04, delta=0.002)
            self.assertAlmostEqual(audio[:rate//2].std(), 0.008, delta=0.0005)
            self.assertEqual(c.load(root / "first/segments.json"), c.load(root / "handoff/segments.json"))
            for file in (*c.PAYLOADS, "manifest.json"):
                self.assertEqual((root / "first" / file).read_bytes(), (root / "second" / file).read_bytes())

    def test_overlap_moves_both_references_with_the_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source(root, "logistics")
            out = root / "overlap"
            c.write_control(root, "logistics-overlap", out)
            audio, rate = sf.read(out / "call.wav")
            self.assertAlmostEqual(audio[round(1.1 * rate)], 0.3, places=3)
            self.assertEqual(c.load(out / "segments.json")[1],
                             {"speaker_id": "B", "start_seconds": 1.0, "end_seconds": 2.0})
            self.assertEqual(c.load(out / "transcript.json")["segments"][1],
                             {"speaker": "B", "text": "B", "start": 1.0, "end": 2.0})

    def test_silence_has_exactly_twelve_seconds_and_no_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "silence"
            c.write_control(root, "silence", out)
            data, rate = sf.read(out / "call.wav", dtype="int16")
            self.assertEqual((rate, data.shape, np.count_nonzero(data)), (16000, (192000,), 0))
            self.assertEqual(c.load(out / "segments.json"), [])
            self.assertEqual(c.load(out / "transcript.json"), {"segments": [], "text": ""})


class CollectionVerification(unittest.TestCase):
    def test_reuse_and_check_refuse_a_modified_reference_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "reference.json"
            c.write_control(root, "silence", root / "silence")
            reference.write_text(json.dumps({"silence": {
                file: c.digest(root / "silence" / file) for file in c.PAYLOADS}}))
            with mock.patch.object(c, "SCRIPTS", {}), mock.patch.object(c, "CONTROLS", {"silence": (None, None)}), \
                    mock.patch.object(c, "REFERENCE", reference), contextlib.redirect_stdout(io.StringIO()):
                c.build(root)
                (root / "silence/transcript.json").write_text("{}")
                for check_only in (True, False):
                    with self.assertRaisesRegex(ValueError, "silence/transcript.json"):
                        c.build(root, check_only=check_only)
                self.assertEqual((root / "silence/transcript.json").read_text(), "{}")

    def test_incomplete_generation_does_not_publish_a_partial_recording(self):
        def fail(argv, **kwargs):
            staged = Path(argv[-2])
            staged.mkdir()
            (staged / "call.wav").write_bytes(b"partial")
            raise OSError("interrupted synthesis")
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(c.subprocess, "run", side_effect=fail):
            root = Path(tmp)
            with self.assertRaisesRegex(OSError, "interrupted synthesis"):
                c.build(root)
            self.assertEqual(list(root.iterdir()), [])
