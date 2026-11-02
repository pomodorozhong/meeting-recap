"""Keep substantial English fixtures and route their synthesis as English."""
import contextlib
import io
import json
from pathlib import Path
import re
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

import numpy as np

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
import collection
import generate


class EnglishCorpusCoverage(unittest.TestCase):
    def test_english_corpus_has_substantial_size_and_speaker_variety(self):
        scripts = [json.loads(path.read_text()) for path in collection.SCRIPTS.values()]
        english = [script for script in scripts if script.get("language") == "en"]
        words = sum(len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)*", turn["text"]))
                    for script in english for turn in script["turns"])
        voices = {speaker["voice"] for script in english
                  for speaker in script["speakers"].values()}
        speaker_counts = {len(script["speakers"]) for script in english}
        self.assertGreaterEqual(len(english), 6)
        self.assertGreaterEqual(words, 2400)
        self.assertGreaterEqual(len(voices), 5)
        self.assertTrue({1, 2, 3, 4}.issubset(speaker_counts))

    def test_registered_english_scripts_are_tagged_and_contain_no_cjk(self):
        for name, path in collection.SCRIPTS.items():
            script = json.loads(path.read_text())
            if name.startswith("english-"):
                with self.subTest(script=name):
                    self.assertEqual(script.get("language"), "en")
            if script.get("language") == "en":
                for index, turn in enumerate(script["turns"]):
                    with self.subTest(script=name, turn=index + 1):
                        self.assertRegex(turn["text"], r"[A-Za-z]")
                        self.assertNotRegex(turn["text"], r"[\u3400-\u9fff]")


class FixtureLanguage(unittest.TestCase):
    def test_legacy_configuration_keeps_default_metadata(self):
        config = generate.voice_configuration({"A": {"voice": "aiden"}})
        self.assertEqual(config, {"model": {generate.MODEL[0]: generate.MODEL[1]}})

    def test_explicit_language_is_recorded_and_invalid_language_rejected(self):
        speakers = {"A": {"voice": "aiden"}}
        for language in ("en", "zh"):
            with self.subTest(language=language):
                config = generate.voice_configuration(speakers, language)
                self.assertEqual(config["language"], language)
                self.assertEqual(config["model"], {generate.MODEL[0]: generate.MODEL[1]})
        with self.assertRaisesRegex(ValueError, "unsupported script language"):
            generate.voice_configuration(speakers, "unknown")

    def test_qwen_receives_fixture_language_at_normal_entry_point(self):
        samples = (0.1 * np.sin(2 * np.pi * 220 * np.arange(16000) / 16000)).astype("float32")
        for language, expected in (("en", "english"), (None, "chinese")):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                text = "Please confirm the delivery time."
                script = {"speakers": {"A": {"voice": "aiden"}},
                          "turns": [{"speaker": "A", "text": text}]}
                if language is not None:
                    script["language"] = language
                path = root / "script.json"
                path.write_text(json.dumps(script))
                qwen = SimpleNamespace(sample_rate=16000, generate=mock.Mock(
                    return_value=[SimpleNamespace(audio=samples)]))
                core = ModuleType("mlx.core")
                core.random = SimpleNamespace(seed=mock.Mock())
                mlx = ModuleType("mlx")
                mlx.__path__ = []
                mlx.core = core
                utils = ModuleType("mlx_audio.tts.utils")
                utils.load_model = mock.Mock(return_value=qwen)
                audio = ModuleType("mlx_audio")
                audio.__path__ = []
                tts = ModuleType("mlx_audio.tts")
                tts.__path__ = []
                audio.tts = tts
                tts.utils = utils
                modules = {"mlx": mlx, "mlx.core": core, "mlx_audio": audio,
                           "mlx_audio.tts": tts, "mlx_audio.tts.utils": utils}
                with mock.patch.dict(sys.modules, modules), contextlib.redirect_stdout(io.StringIO()):
                    generate.generate(path, root / "out", 7)
                qwen.generate.assert_called_once_with(text=text, voice="aiden", lang_code=expected)
                manifest = json.loads((root / "out/manifest.json").read_text())
                if language is None:
                    self.assertNotIn("language", manifest)
                else:
                    self.assertEqual(manifest["language"], language)
