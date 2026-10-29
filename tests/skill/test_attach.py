import json
import unittest

from helpers import DatasetCase, segs, transcript, write_json

import attach

DIARIZATION = segs(("A", 0, 5), ("B", 5, 10))
ASR = transcript(("你", 1, 2), ("好", 2, 3), ("<|zh|>嗨", 6, 7))


class LabelAt(unittest.TestCase):
    def test_largest_overlap_wins(self):
        self.assertEqual(attach.label_at(DIARIZATION, 4, 7), "B")

    def test_nearest_label_within_one_second(self):
        gap = segs(("A", 0, 5), ("B", 8, 10))
        self.assertEqual(attach.label_at(gap, 5.4, 5.6), "A")
        self.assertIsNone(attach.label_at(gap, 6.2, 6.6))


class Turns(unittest.TestCase):
    def test_word_attachment_merges_runs_and_strips_tokens(self):
        out = attach.turns(ASR, DIARIZATION, "word")
        self.assertEqual([(t["speaker_id"], t["text"]) for t in out], [("A", "你好"), ("B", "嗨")])
        self.assertEqual((out[0]["start_seconds"], out[0]["end_seconds"]), (1, 3))

    def test_word_attachment_needs_word_timestamps(self):
        with self.assertRaises(ValueError):
            attach.turns({"segments": [{"start": 0, "end": 1, "text": "x"}]}, DIARIZATION, "word")

    def test_line_attachment_looks_up_the_end_second(self):
        # Ends at 6.5 s, so the end-second lookup finds B although A covers more of the line.
        asr = {"segments": [{"start": 3, "end": 6.5, "text": "x"}]}
        self.assertEqual(attach.turns(asr, DIARIZATION, "line")[0]["speaker_id"], "B")
        self.assertEqual(attach.turns(asr, DIARIZATION, "seg")[0]["speaker_id"], "A")

    def test_unassigned_text(self):
        out = attach.turns(transcript(("x", 20, 21)), DIARIZATION, "word")
        self.assertEqual(out[0]["speaker_id"], "__unassigned__")


class Attach(DatasetCase):
    def setUp(self):
        super().setUp()
        self.add_recording("rec1", 30)
        self.add_recording("rec2", 30)
        self.add_run("dia1", artifacts={"segments": DIARIZATION})
        self.add_run("asr1", artifacts={"transcript": ASR})

    def test_creates_a_derived_run(self):
        info = attach.attach(self.root, "asr1", "dia1", "att1", "word")
        self.assertEqual(info["parents"], ["asr1", "dia1"])
        data = json.loads((self.root / info["artifacts"]["segments"]["path"]).read_text())
        self.assertEqual(data[0]["speaker_id"], "A")
        with self.assertRaises(ValueError):
            attach.attach(self.root, "asr1", "dia1", "att1", "word")

    def test_rejects_mismatched_or_changed_parents(self):
        self.add_run("dia2", recording_id="rec2", artifacts={"segments": DIARIZATION})
        with self.assertRaises(ValueError):
            attach.attach(self.root, "asr1", "dia2", "att2", "word")
        self.add_run("dia3", artifacts={"segments": DIARIZATION}, status="failed")
        with self.assertRaises(ValueError):
            attach.attach(self.root, "asr1", "dia3", "att3", "word")
        write_json(self.root / "runs" / "dia1" / "segments.json", segs(("Z", 0, 9)))
        with self.assertRaises(ValueError):
            attach.attach(self.root, "asr1", "dia1", "att4", "word")


if __name__ == "__main__":
    unittest.main()
