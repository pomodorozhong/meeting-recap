"""Verify runner download/load boundaries with fake models; no weights or ML packages needed."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]


def runner(folder):
    spec = importlib.util.spec_from_file_location(f"{folder}_runner", ROOT / "experiments" / folder / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ModelPins(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "output.json"

    def invoke(self, module, arguments, modules):
        with patch.object(sys, "argv", [module.__file__, *map(str, arguments)]), patch.dict(sys.modules, modules), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            module.main()

    def test_mlx_loads_the_pinned_snapshot_and_records_its_revision(self):
        module = runner("mlx")
        for repo, pin in module.MODELS.items():
            with self.subTest(repo=repo):
                snapshot = Path(self.temp.name) / "snapshots" / pin
                download = Mock(return_value=str(snapshot))
                transcribe = Mock(return_value={"text": "synthetic", "segments": []})
                self.invoke(module, ["input.wav", self.out, repo], {
                    "huggingface_hub": SimpleNamespace(snapshot_download=download),
                    "mlx_whisper": SimpleNamespace(transcribe=transcribe)})
                download.assert_called_once_with(repo_id=repo, revision=pin)
                self.assertEqual(transcribe.call_args.kwargs["path_or_hf_repo"], str(snapshot))
                self.assertEqual(json.loads(self.out.read_text())["model_revision"], pin)

    def test_mlx_rejects_a_download_that_resolves_to_a_different_snapshot(self):
        transcribe = Mock()
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.invoke(runner("mlx"), ["input.wav", self.out, "mlx-community/whisper-large-v3-mlx"], {
                "huggingface_hub": SimpleNamespace(snapshot_download=Mock(return_value="/cache/snapshots/main")),
                "mlx_whisper": SimpleNamespace(transcribe=transcribe)})
        transcribe.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_unpinned_models_and_moving_revision_names_are_rejected(self):
        for folder, arguments in [
            ("mlx", ["input.wav", self.out, "example/unlisted"]),
            ("mlx", ["input.wav", self.out, "example/unlisted", "--revision", "main"]),
            ("pyannote", ["input.wav", self.out, "--revision", "main"]),
        ]:
            with self.subTest(folder=folder, arguments=arguments), self.assertRaises(SystemExit) as error:
                self.invoke(runner(folder), arguments, {})
            self.assertEqual(error.exception.code, 2)
        self.assertFalse(self.out.exists())

    def pyannote_modules(self, loaded):
        loader = Mock(return_value=loaded)
        modules = {"torch": SimpleNamespace(backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False)),
                                            device=lambda name: name),
                   "pyannote": SimpleNamespace(),
                   "pyannote.audio": SimpleNamespace(Pipeline=SimpleNamespace(from_pretrained=loader))}
        return modules, loader

    def test_pyannote_pins_bundled_assets_and_writes_registration_metadata(self):
        annotation = SimpleNamespace(itertracks=Mock(return_value=[(SimpleNamespace(start=0, end=1), None, "A")]))
        model = Mock(return_value=SimpleNamespace(exclusive_speaker_diarization=annotation))
        modules, loader = self.pyannote_modules(model)
        self.invoke(runner("pyannote"), ["input.wav", self.out, 2], modules)
        pin = "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"
        loader.assert_called_once_with("pyannote/speaker-diarization-community-1", revision=pin)
        model.assert_called_once_with("input.wav", num_speakers=2)
        metadata = json.loads(self.out.with_suffix(".metadata.json").read_text())
        self.assertEqual(metadata["model_revision"], pin)
        self.assertEqual(metadata["config"], {"num_speakers": 2})
        self.assertEqual(json.loads(self.out.read_text())[0]["speaker_id"], "A")

    def test_pyannote_does_not_write_a_completed_output_after_a_failed_load(self):
        modules, _ = self.pyannote_modules(None)
        with self.assertRaisesRegex(RuntimeError, "authenticate"):
            self.invoke(runner("pyannote"), ["input.wav", self.out], modules)
        self.assertFalse(self.out.exists())
        self.assertFalse(self.out.with_suffix(".metadata.json").exists())
