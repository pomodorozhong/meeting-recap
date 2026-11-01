"""Scoring a run against the synthetic call, on generated run files and the committed reference."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/synthetic-call"))

import score_recap  # noqa: E402
import score_speakers  # noqa: E402


def write(directory, name, data):
    path = Path(directory) / name
    path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False))
    return path


class Speakers(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.reference = Path(self.temporary.name)
        write(self.reference, "manifest.json", {"call_sha256": "abc"})
        write(self.reference, "segments.json", [
            {"speaker_id": "A", "start_seconds": 0.0, "end_seconds": 2.0},
            {"speaker_id": "B", "start_seconds": 2.0, "end_seconds": 4.0}])
        write(self.reference, "transcript.json", {"segments": [
            {"speaker": "A", "text": "你好嗎？"}, {"speaker": "B", "text": "很好啊。"}]})
        # Whisper put B's first character 「很」 inside A's time, so it lands in A's turn.
        self.asr = {"segments": [{"text": "你好嗎很好啊", "start": 0, "end": 4, "words": [
            {"word": "<|zh|>你", "start": 0.1, "end": 0.5}, {"word": "好", "start": 0.5, "end": 0.9},
            {"word": "嗎", "start": 0.9, "end": 1.3}, {"word": "很", "start": 1.5, "end": 1.9},
            {"word": "好", "start": 2.1, "end": 2.3}, {"word": "啊", "start": 2.6, "end": 3.0}]}]}
        # The diarizer splits B's voice over two labels.
        self.segments = [{"speaker_id": "X", "start_seconds": 0.0, "end_seconds": 2.0},
                         {"speaker_id": "Y", "start_seconds": 2.0, "end_seconds": 2.4},
                         {"speaker_id": "Z", "start_seconds": 2.4, "end_seconds": 4.0}]
        self.turns = [{"speaker_id": "X", "text": "你好嗎很"}, {"speaker_id": "Y", "text": "好"},
                      {"speaker_id": "Z", "text": "啊"}]

    def tearDown(self):
        self.temporary.cleanup()

    def score(self, **kwargs):
        args = {"asr": self.asr, "segments": self.segments, "audio_sha256": "abc", "turns": self.turns,
                "reference": self.reference, "simplify": lambda text: text, **kwargs}
        return score_speakers.score(**args)

    def test_split_labels_map_to_one_speaker_and_boundary_drift_counts_only_in_the_transcript(self):
        result = self.score()
        self.assertEqual(result["mapping"], {"X": "A", "Y": "B", "Z": "B"})
        self.assertEqual(result["diarization"]["rate"], 1.0)  # every word's own time agrees
        self.assertEqual((result["transcript"]["aligned"], result["transcript"]["agree"]), (6, 5))
        self.assertEqual(result["transcript"]["errors"], {"B->A": 1})

    def test_turns_are_optional(self):
        self.assertNotIn("transcript", self.score(turns=None))

    def test_audio_of_another_call_is_refused(self):
        with self.assertRaises(ValueError):
            self.score(audio_sha256="other")

    def test_text_without_word_times_is_refused(self):
        with self.assertRaises(ValueError):
            self.score(asr={"segments": [{"text": "你好", "start": 0, "end": 1, "words": []}]})


class Recap(unittest.TestCase):
    """A two-item key on the committed reference's first turns (0: A asks, 1: B answers, 2: C agrees)."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.key = write(root, "key.json", {"items": [
            {"id": "D1", "accept": ["decisions"], "text": "they can hear each other", "turns": [1, 2]},
            {"id": "T1", "accept": ["action_items"], "text": "start", "turns": [3], "owner": "A", "due": None}],
            "answered": [{"id": "X1", "text": "can you hear me? yes", "turns": [0, 1]}]})
        self.run = root / "run"
        self.run.mkdir()
        write(self.run, "transcript.md", "**[00:00:00] Host:** 哈囉，聽得到嗎？\n\n**[00:00:03] Guest:** 聽得到。\n\n"
                                         "**[00:00:06] Host:** 好，那我們開始吧。\n")
        write(self.run, "names.json", {"Host": "A", "Guest": "B"})
        write(self.run, "summary.json", {"notes": {
            "topics": [],
            "decisions": [{"text": "both can hear", "evidence": ["00:00:03"]}],
            "action_items": [{"task": "start", "owner": "Guest", "due": None, "evidence": ["00:00:06"]}],
            "proposals": [],
            "open_questions": [{"text": "can you hear me?", "evidence": ["00:00:00"]}]}})
        self.matches = {"items": {
            "decisions/0": {"verdict": "correct", "matches": ["D1"]},
            "action_items/0": {"verdict": "correct", "matches": ["T1"]},
            "open_questions/0": {"verdict": "wrong", "matches": ["X1"], "note": "answered"}}}

    def tearDown(self):
        self.temporary.cleanup()

    def test_scores_found_items_evidence_owners_and_errors(self):
        result = score_recap.score(self.run, self.matches, self.key)
        self.assertEqual(result["found"], ["D1", "T1"])
        self.assertEqual(result["placed_correctly"], 2)
        self.assertEqual(result["evidence_covers_item"], 2)
        self.assertEqual(result["owner_errors"], ["action_items/0 (T1): owner B, should be A"])  # Guest is B
        self.assertEqual(result["errors"], ["open_questions/0: answered"])

    def test_every_recap_item_needs_a_verdict(self):
        del self.matches["items"]["decisions/0"]
        with self.assertRaises(ValueError):
            score_recap.score(self.run, self.matches, self.key)


if __name__ == "__main__":
    unittest.main()
