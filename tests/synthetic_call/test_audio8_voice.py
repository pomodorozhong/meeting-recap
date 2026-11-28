"""Check the Audio8 re-voicing setup without loading the model."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
import generate_audio8


class Audio8Voices(unittest.TestCase):
    def test_model_is_pinned_to_a_commit(self):
        model = generate_audio8.provenance()["model"]
        self.assertRegex(model["revision"], r"^[0-9a-f]{40}$")

    def test_every_collection_language_has_a_reference_sentence(self):
        pin = generate_audio8.provenance()
        for voice, language in generate_audio8.references_needed(generate_audio8.SCRIPTS):
            self.assertIn(language, pin["reference_text"], voice)

    def test_each_voice_gets_its_own_reference_per_language(self):
        needed = generate_audio8.references_needed(["handoff", "english-handoff"])
        self.assertEqual(needed, [("aiden", "en"), ("dylan", "zh"), ("emotivoice-1012", "en"),
                                  ("f5-news-female", "zh")])

    def test_cached_references_are_reused_and_f5_uses_its_pinned_clip(self):
        pin = generate_audio8.provenance()
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "dylan-zh.wav").write_bytes(b"cached")
            original = generate_audio8.reference_path
            generate_audio8.reference_path = lambda reference: Path("f5-reference.wav")
            try:
                references = generate_audio8.render_references(
                    folder, [("dylan", "zh"), ("f5-news-female", "zh")], pin)
            finally:
                generate_audio8.reference_path = original
        self.assertEqual(references["dylan", "zh"], (folder / "dylan-zh.wav", pin["reference_text"]["zh"]))
        f5_text = json.loads((HERE / "reference/f5-voice.json").read_text())["reference"]["text"]
        self.assertEqual(references["f5-news-female", "zh"], (Path("f5-reference.wav"), f5_text))


if __name__ == "__main__":
    unittest.main()
