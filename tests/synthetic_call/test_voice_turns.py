"""The per-voice check finds English terms in Mandarin lines and adds up each voice's results."""
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
import check_voice_turns as turns


class VoiceTurns(unittest.TestCase):
    def test_terms_are_the_latin_words_of_a_line(self):
        self.assertEqual(turns.english_terms("等一下，timeout 的原因已經找到了嗎？"), ["timeout"])
        self.assertEqual(turns.english_terms("先接 USB，再看 API 的 log。"), ["USB", "API", "log"])
        self.assertEqual(turns.english_terms("沒有英文"), [])

    def test_terms_are_heard_as_whole_words_ignoring_case_spaces_and_hyphens(self):
        for decoded in ("等一下,Time Out的原因", "TIMEOUT", "time-out 的原因"):
            self.assertTrue(turns.heard("timeout", decoded), decoded)
        for decoded in ("Time Mode的原因", "timeouts", "KaiNyodo", "超時"):
            self.assertFalse(turns.heard("timeout", decoded), decoded)
        self.assertTrue(turns.heard("log", "昨晚的Log匯出"))
        self.assertTrue(turns.heard("login", "第一个是login page的bug"))
        self.assertTrue(turns.heard("team", "Demo给Product Team。"))
        self.assertTrue(turns.heard("multi-stage", "先改成Multi Stage Build"))
        self.assertFalse(turns.heard("unit", "包含写Unitest"))
        self.assertFalse(turns.heard("log", "logbook"))

    def test_voices_add_up_by_language(self):
        voices = turns.summarize([
            {"voice": "a", "language": "zh", "errors": 1, "units": 10, "terms": {"log": True, "API": False}},
            {"voice": "a", "language": "zh", "errors": 0, "units": 10, "terms": {}},
            {"voice": "a", "language": "en", "errors": 2, "units": 8, "terms": {}},
            {"voice": "b", "language": "en", "errors": 0, "units": 5, "terms": {}},
        ])
        self.assertEqual((voices["a"]["terms_heard"], voices["a"]["terms"]), (1, 2))
        self.assertAlmostEqual(voices["a"]["zh_cer"], 0.05)
        self.assertAlmostEqual(voices["a"]["en_wer"], 0.25)
        self.assertIsNone(voices["b"]["zh_cer"])
        self.assertEqual(voices["b"]["en_wer"], 0.0)


if __name__ == "__main__":
    unittest.main()
