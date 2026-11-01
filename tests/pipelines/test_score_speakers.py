"""The synthetic-call speaker scoring, on generated run and reference files."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/pipelines/whisper-sortformer"))

import score_speakers  # noqa: E402


def write(directory, name, data):
    (directory / name).write_text(json.dumps(data, ensure_ascii=False))


class ScoreSpeakers(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.run, self.reference = root / "run", root / "reference"
        self.run.mkdir()
        self.reference.mkdir()
        write(self.reference, "manifest.json", {"call_sha256": "abc"})
        write(self.reference, "segments.json", [
            {"speaker_id": "A", "start_seconds": 0.0, "end_seconds": 2.0},
            {"speaker_id": "B", "start_seconds": 2.0, "end_seconds": 4.0}])
        write(self.reference, "transcript.json", {"segments": [
            {"speaker": "A", "text": "你好嗎？"}, {"speaker": "B", "text": "很好啊。"}]})
        write(self.run, "run.json", {"input_sha256": "abc", "diarizer": "who"})
        # Whisper put B's first character 「很」 at the end of A's time, so it lands in A's turn.
        write(self.run, "asr.json", {"segments": [{"text": "你好嗎很好啊", "start": 0, "end": 4, "words": [
            {"word": "你", "start": 0.1, "end": 0.5}, {"word": "好", "start": 0.5, "end": 0.9},
            {"word": "嗎", "start": 0.9, "end": 1.3}, {"word": "很", "start": 1.5, "end": 1.9},
            {"word": "好", "start": 2.1, "end": 2.3},
            {"word": "啊", "start": 2.6, "end": 3.0}]}]})
        # The diarizer splits B's voice over two labels.
        write(self.run, "diarization.json", [
            {"speaker_id": "X", "start_seconds": 0.0, "end_seconds": 2.0},
            {"speaker_id": "Y", "start_seconds": 2.0, "end_seconds": 2.4},
            {"speaker_id": "Z", "start_seconds": 2.4, "end_seconds": 4.0}])
        write(self.run, "turns.json", [{"speaker_id": "X", "text": "你好嗎很"}, {"speaker_id": "Y", "text": "好"},
                                         {"speaker_id": "Z", "text": "啊"}])

    def tearDown(self):
        self.temporary.cleanup()

    def score(self):
        return score_speakers.score(self.run, self.reference, simplify=lambda text: text)

    def test_split_labels_map_to_one_speaker_and_boundary_drift_counts_only_in_the_transcript(self):
        result = self.score()
        self.assertEqual(result["mapping"], {"X": "A", "Y": "B", "Z": "B"})
        self.assertEqual(result["diarization"]["rate"], 1.0)  # every word's own time agrees
        self.assertEqual(result["transcript"]["aligned"], 6)
        self.assertEqual(result["transcript"]["agree"], 5)  # 「很」 is in A's turn
        self.assertEqual(result["transcript"]["errors"], {"B->A": 1})

    def test_a_run_of_another_call_is_refused(self):
        write(self.run, "run.json", {"input_sha256": "other"})
        with self.assertRaises(ValueError):
            self.score()


if __name__ == "__main__":
    unittest.main()
