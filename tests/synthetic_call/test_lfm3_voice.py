"""Check the LFM3 re-voicing setup without loading the model."""
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "lfm3-audio"))
import generate_lfm3
import tts_render as render


class LFM3Voices(unittest.TestCase):
    def test_every_collection_voice_maps_to_a_gender(self):
        pin = generate_lfm3.provenance()
        for name, path in generate_lfm3.SCRIPTS.items():
            script = json.loads(path.read_text())
            voices = generate_lfm3.lfm3_voices(script["speakers"], pin)
            self.assertEqual(set(voices), set(script["speakers"]), name)
            self.assertIn(script.get("language", "zh"), pin["languages"], name)

    def test_old_voice_genders(self):
        pin = generate_lfm3.provenance()
        voices = generate_lfm3.lfm3_voices({
            "A": {"voice": "f5-news-female"}, "B": {"voice": "ryan"},
            "C": {"voice": "emotivoice-1066"}}, pin)
        self.assertEqual(voices, {"A": "female", "B": "male", "C": "female"})

    def test_unknown_voice_is_refused(self):
        with self.assertRaisesRegex(ValueError, "no LFM3 voice"):
            generate_lfm3.lfm3_voices({"A": {"voice": "new-voice"}}, generate_lfm3.provenance())

    def test_model_is_pinned_to_a_commit(self):
        model = generate_lfm3.provenance()["model"]
        self.assertRegex(model["revision"], r"^[0-9a-f]{40}$")

    def test_request_validation(self):
        good = {"seed": 7, "language": "zh", "turns": [{"index": 0, "gender": "male", "text": "好"}]}
        bad = [
            {**good, "seed": True},
            {**good, "language": "fr"},
            {**good, "turns": [{"index": 0, "gender": "child", "text": "好"}]},
            {**good, "turns": [{"index": 0, "gender": "male", "text": " "}]},
            {**good, "turns": [{"index": 0, "gender": "male", "text": "好"}] * 2},
        ]
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "request.json"
            path.write_text(json.dumps(good))
            self.assertEqual(render.load_request(path), good)
            for request in bad:
                path.write_text(json.dumps(request))
                with self.assertRaises(ValueError, msg=request):
                    render.load_request(path)


if __name__ == "__main__":
    unittest.main()
