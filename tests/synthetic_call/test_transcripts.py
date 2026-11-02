"""Language regressions must stay visible even if the other group improves."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import wave

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
import score_transcripts as scoring


def report(english, chinese):
    return {"groups": {"en": {"rate": english, "metric": "wer", "errors": 0,
                              "reference_units": 100, "calls": 1},
                       "zh": {"rate": chinese, "metric": "cer", "errors": 0,
                              "reference_units": 100, "calls": 1}},
            "references": {"example": "fixed"}, "normalizers": {"example": "fixed"}}


class LanguageComparison(unittest.TestCase):
    def test_english_regression_fails_even_when_chinese_improves(self):
        result = scoring.compare(report(.06, .01), report(.02, .08))
        self.assertFalse(result["passed"])
        self.assertFalse(result["languages"]["en"]["passed"])
        self.assertTrue(result["languages"]["zh"]["passed"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = root / "baseline.json"
            baseline.write_text(json.dumps(report(.02, .08)))
            argv = ["score_transcripts.py", str(root / "fixtures"), str(root / "runs"),
                    "--output", str(root / "report.json"), "--baseline", str(baseline)]
            with mock.patch.object(sys, "argv", argv), \
                    mock.patch.object(scoring, "score", return_value=report(.06, .01)), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(scoring.main(), 1)

    def test_comparison_requires_both_groups_and_same_reference(self):
        baseline = report(.02, .08)
        del baseline["groups"]["en"]
        with self.assertRaisesRegex(ValueError, "both"):
            scoring.compare(report(.02, .08), baseline)
        baseline = report(.02, .08)
        baseline["references"] = {"other": "different"}
        with self.assertRaisesRegex(ValueError, "different audio"):
            scoring.compare(report(.02, .08), baseline)
        with self.assertRaises(ValueError):
            scoring.compare(report(.02, .08), report(.02, .08), float("nan"))

    def test_baseline_cannot_be_overwritten_by_a_new_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = root / "baseline.json"
            baseline.write_text(json.dumps(report(.02, .08)))
            before = baseline.read_bytes()
            argv = ["score_transcripts.py", str(root), str(root),
                    "--output", str(baseline), "--baseline", str(baseline)]
            with mock.patch.object(sys, "argv", argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    scoring.main()
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(baseline.read_bytes(), before)

    def test_edit_distance_counts_word_substitutions_deletions_and_insertions(self):
        self.assertEqual(scoring.edit_distance(["can", "not", "ship"], ["can", "ship", "now"]), 2)

    def test_source_script_cannot_be_overwritten_by_a_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "script.json"
            script.write_text('{"language": "en"}')
            before = script.read_bytes()
            argv = ["score_transcripts.py", str(root / "fixtures"), str(root / "runs"),
                    "--output", str(script)]
            with mock.patch.object(scoring, "SCRIPTS", {"english": script}), \
                    mock.patch.object(sys, "argv", argv), \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    scoring.main()
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(script.read_bytes(), before)


class CorpusTranscriptScoring(unittest.TestCase):
    def test_numbers_and_contractions_normalize_and_missing_english_run_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixtures, runs = root / "fixtures", root / "runs"
            scripts = {}
            cases = {"english": ("en", "We need seven copies, and we're ready.",
                                 "We need 7 copies and we are ready."),
                     "chinese": ("zh", "我們需要七份資料。", "我们需要七份资料。")}
            for name, (language, intended, actual) in cases.items():
                folder = fixtures / name
                folder.mkdir(parents=True)
                with wave.open(str(folder / "call.wav"), "wb") as audio:
                    audio.setnchannels(1)
                    audio.setsampwidth(2)
                    audio.setframerate(16000)
                    audio.writeframes(b"\0\0" * 160)
                audio_hash = hashlib.sha256((folder / "call.wav").read_bytes()).hexdigest()
                (folder / "manifest.json").write_text(json.dumps(
                    {"call_sha256": audio_hash, "language": language}))
                (folder / "transcript.json").write_text(json.dumps({"text": intended}))
                script = root / (name + ".json")
                script.write_text(json.dumps({"language": language}))
                scripts[name] = script
                output = runs / name
                output.mkdir(parents=True)
                (output / "asr.json").write_text(json.dumps(
                    {"text": actual, "audio_sha256": audio_hash}))
            with mock.patch.object(scoring, "SCRIPTS", scripts):
                result = scoring.score(fixtures, runs)
                self.assertEqual(result["groups"]["en"]["metric"], "wer")
                self.assertEqual(result["groups"]["zh"]["metric"], "cer")
                self.assertEqual(result["groups"]["en"]["rate"], 0)
                self.assertEqual(result["groups"]["zh"]["rate"], 0)
                (runs / "english/asr.json").unlink()
                with self.assertRaises(FileNotFoundError):
                    scoring.score(fixtures, runs)
