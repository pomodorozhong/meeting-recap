import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
from collection import digest, make
from score_case import edit_distance, speaker_time


def seg(who, start, end):
    return {"speaker_id": who, "start_seconds": start, "end_seconds": end}


class CollectionTest(unittest.TestCase):
    def test_overlap_counts_both_voices_and_penalizes_split_labels(self):
        truth = [seg("A", 0, 2), seg("B", 1, 3)]
        hyp = [seg("X", 0, 1), seg("Y", 1, 2), seg("Z", 2, 4)]
        result = speaker_time(truth, hyp, 4)
        self.assertEqual(result["reference_s"], 4)
        self.assertEqual(result["miss_s"], 1)
        self.assertEqual(result["false_alarm_s"], 1)
        self.assertEqual(result["confusion_s"], 1)
        self.assertEqual(result["error_rate"], 0.75)

    def test_full_benchmark_refuses_another_checkout_before_generating(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "checkout"
            (repo / ".git").mkdir(parents=True)
            alias = Path(tmp) / "linked"
            alias.symlink_to(repo, target_is_directory=True)
            result = subprocess.run([HERE / "benchmark.sh", alias / "runs"], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside any Git checkout", result.stderr)
            self.assertFalse((repo / "runs").exists())

    def test_silence_has_no_rate_and_counts_false_activity(self):
        self.assertEqual(edit_distance("", "word"), 4)
        self.assertEqual(edit_distance("aba", "abc"), 1)
        self.assertEqual(edit_distance("ba", "aba"), 1)
        self.assertEqual(edit_distance("aba", "ba"), 1)
        result = speaker_time([], [seg("X", 0, 2), seg("X", 1, 4)], 3)
        self.assertEqual(result["false_alarm_s"], 3)
        self.assertIsNone(result["error_rate"])

    def test_control_moves_reference_with_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "logistics"
            source.mkdir()
            signal = np.zeros(48000)
            signal[8000:24000] = 0.1
            signal[28800:44800] = 0.2
            sf.write(source / "call.wav", signal, 16000)
            truth = [seg("A", 0.5, 1.5), seg("B", 1.8, 2.8)]
            (source / "segments.json").write_text(json.dumps(truth))
            (source / "manifest.json").write_text(json.dumps({"call_sha256": digest(source / "call.wav")}))
            (source / "transcript.json").write_text(json.dumps({"segments": [
                {"speaker": who, "text": who} for who in "AB"]}))
            make(root, "logistics-overlap", "logistics")
            out = root / "logistics-overlap"
            audio, sr = sf.read(out / "call.wav")
            self.assertAlmostEqual(audio[int(sr * 1.1)], 0.3, places=3)
            turns = json.loads((out / "transcript.json").read_text())
            self.assertEqual(turns["segments"][1]["start"], 1)
            self.assertEqual(json.loads((out / "manifest.json").read_text())["call_sha256"], digest(out / "call.wav"))
            with self.assertRaises(FileExistsError):
                make(root, "logistics-overlap", "logistics")
