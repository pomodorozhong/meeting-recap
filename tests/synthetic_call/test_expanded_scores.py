"""Boundary cases for time-based errors and zero-run splitting."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments/synthetic-call"))
from expanded_followup import chunks
from expanded_scores import speaker_time


class ExpandedMetrics(unittest.TestCase):
    @staticmethod
    def seg(label, start, end):
        return {"speaker_id": label, "start_seconds": start, "end_seconds": end}

    def test_merge_during_overlap_and_false_alarm_on_silence(self):
        # Five seconds of simultaneous speech count twice in the denominator.
        ref = [self.seg("A", 0, 10), self.seg("B", 5, 10)]
        hyp = [self.seg("X", 0, 11)]
        row = speaker_time(ref, hyp, 12)
        self.assertEqual((row["reference_s"], row["miss_s"], row["false_alarm_s"]), (15, 5, 1))
        self.assertAlmostEqual(row["error_rate"], 6 / 15)
        silent = speaker_time([], hyp, 12)
        self.assertIsNone(silent["error_rate"])
        self.assertEqual(silent["false_alarm_s"], 11)

    def test_exact_zero_split_keeps_quiet_signal_and_original_offsets(self):
        x = np.ones(120, dtype="int16")
        x[20:70] = 0
        self.assertEqual(chunks(x, rate=10), [(0, 22), (68, 120)])
        x[45] = 1
        self.assertEqual(chunks(x, rate=10), [(0, 120)])
        self.assertEqual(chunks(np.zeros_like(x), rate=10), [])
