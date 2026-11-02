"""The voice gate requires whole English tokens in their original turns."""
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
import check_voice as voice


class VoiceGate(unittest.TestCase):
    def test_homophones_translations_and_split_or_suffixed_words_fail(self):
        self.assertTrue(voice.contains_term("昨晚的Log匯出", "log"))
        self.assertTrue(voice.contains_term("等一下，Timeout的原因", "timeout"))
        for text in ("logbook", "locker", "log2", "日誌", "烙庫"):
            self.assertFalse(voice.contains_term(text, "log"))
        for text in ("time out", "timeouts", "timeout2", "超時", "time mode"):
            self.assertFalse(voice.contains_term(text, "timeout"))

    def test_words_in_wrong_turns_fail_even_when_whole_text_matches(self):
        text = "我反對中午以前把log匯出等一下timeout的原因"
        spans = [(0.5, 2.0), (2.3, 5.0), (7.4, 10.0)]
        correct = {"segments": [{"words": [
            {"word": "log", "start": 3.0, "end": 3.4},
            {"word": "timeout", "start": 8.0, "end": 8.4}]}]}
        passed = voice.score_decodes({"text": text}, correct, text, spans, lambda value: value)
        self.assertTrue(passed["passed"])
        correct["segments"][0]["words"][0].update(start=8.6, end=9.0)
        failed = voice.score_decodes({"text": text}, correct, text, spans, lambda value: value)
        self.assertEqual(failed["mandarin_similarity"], 1.0)
        self.assertTrue(all(failed["hits"].values()))
        self.assertFalse(failed["timed"]["log"]["in_turn"])
        self.assertFalse(failed["passed"])

    def test_english_hits_do_not_pass_unrelated_mandarin(self):
        timed = {"segments": [{"words": [
            {"word": "log", "start": 3, "end": 4},
            {"word": "timeout", "start": 8, "end": 9}]}]}
        report = voice.score_decodes({"text": "你好log天氣timeout"}, timed,
                                    "我反對中午以前把紀錄匯出原因找到了嗎",
                                    [(0.5, 2), (2.3, 5), (7.4, 10)], lambda value: value)
        self.assertTrue(all(report["hits"].values()))
        self.assertFalse(report["passed"])
