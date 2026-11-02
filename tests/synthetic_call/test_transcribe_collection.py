"""Exercise provenance reuse and publication without loading a speech model."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
import transcribe_collection as transcription


class CollectionTranscription(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fixtures, self.runs = self.root / "fixtures", self.root / "runs"
        self.scripts = {}
        for name, script in (("english", {"language": "en"}), ("mandarin", {})):
            path = self.root / (name + ".json")
            path.write_text(json.dumps(script))
            self.scripts[name] = path
            folder = self.fixtures / name
            folder.mkdir(parents=True)
            (folder / "call.wav").write_bytes(name.encode())
        self.decoder = mock.Mock(return_value={"text": " Hello.", "segments": [{"text": " Hello."}]})
        self.download = mock.Mock(return_value="pinned-local-model")
        patches = [mock.patch.object(transcription, "SCRIPTS", self.scripts),
                   mock.patch.object(transcription, "build"),
                   mock.patch.dict(sys.modules, {"mlx_whisper": SimpleNamespace(transcribe=self.decoder),
                                                 "huggingface_hub": SimpleNamespace(snapshot_download=self.download)}),
                   contextlib.redirect_stdout(io.StringIO())]
        for patch in patches:
            patch.__enter__()
            self.addCleanup(patch.__exit__, None, None, None)

    def test_missing_calls_use_pinned_model_and_per_script_language_then_reuse(self):
        transcription.transcribe_collection(self.fixtures, self.runs)
        self.download.assert_called_once_with(transcription.MODEL["repository"],
                                               revision=transcription.MODEL["revision"],
                                               allow_patterns=["config.json", "weights.npz"])
        self.assertEqual([call.kwargs["language"] for call in self.decoder.call_args_list], ["en", "zh"])
        self.assertTrue(all(call.kwargs["temperature"] == 0
                            and call.kwargs["condition_on_previous_text"] is False
                            for call in self.decoder.call_args_list))
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in self.runs.glob("*/asr.json")}
        self.decoder.reset_mock()
        self.download.reset_mock()
        transcription.transcribe_collection(self.fixtures, self.runs)
        self.decoder.assert_not_called()
        self.download.assert_not_called()
        self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before})

    def test_stale_report_prevents_any_decoding_or_output_mutation(self):
        transcription.transcribe_collection(self.fixtures, self.runs)
        stale = self.runs / "mandarin/asr.json"
        report = json.loads(stale.read_text())
        report["model"]["revision"] = "different"
        stale.write_text(json.dumps(report))
        before = stale.read_bytes()
        (self.runs / "english/asr.json").unlink()
        self.decoder.reset_mock()
        with self.assertRaisesRegex(ValueError, "stale ASR provenance"):
            transcription.transcribe_collection(self.fixtures, self.runs)
        self.decoder.assert_not_called()
        self.assertEqual(stale.read_bytes(), before)
        self.assertFalse((self.runs / "english/asr.json").exists())

    def test_fixture_validation_failure_does_not_create_output(self):
        transcription.build.side_effect = ValueError("different reference audio")
        with self.assertRaisesRegex(ValueError, "different reference audio"):
            transcription.transcribe_collection(self.fixtures, self.runs)
        self.assertFalse(self.runs.exists())
        self.decoder.assert_not_called()

    def test_atomic_publication_preserves_existing_report(self):
        target = self.runs / "example/asr.json"
        provenance = {"audio_sha256": "same"}
        report = {**provenance, "text": "first", "segments": [{"text": "first"}]}
        transcription.publish_report(target, report, provenance)
        before = target.read_bytes()
        other = {**provenance, "text": "second", "segments": [{"text": "second"}]}
        transcription.publish_report(target, other, provenance)
        self.assertEqual(target.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "stale ASR provenance"):
            transcription.publish_report(target, other, {"audio_sha256": "different"})
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(list(target.parent.glob(".asr-*")), [])


if __name__ == "__main__":
    unittest.main()
