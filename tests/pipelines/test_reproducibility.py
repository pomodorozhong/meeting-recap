"""Reproducible setup, tested with small synthetic model bytes and empty caches."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments/pipelines/whisper-sortformer"))
import pins
import recap
import weights


class WeightRecovery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = {"model/weights.bin": b"synthetic weights", "config.json": b"{}"}
        hashes = {name: hashlib.sha256(data).hexdigest() for name, data in self.files.items()}
        tree = hashlib.sha256("".join(f"{name}\0{digest}\n" for name, digest in sorted(hashes.items())).encode()).hexdigest()
        self.spec = {"repo": "fixture/model", "revision": "a" * 40, "files": hashes, "tree_sha256": tree}
        patch = mock.patch.dict(pins.FLUID_MODELS, {"fixture": self.spec})
        patch.start()
        self.addCleanup(patch.stop)

    def download(self, repo, revision, relative, destination):
        self.assertEqual((repo, revision), ("fixture/model", "a" * 40))
        destination.write_bytes(self.files[relative])

    def test_restores_exact_files_and_reuses_matching_cache_without_network(self):
        with mock.patch.object(weights, "download", side_effect=self.download) as download:
            folder = weights.install("fixture", self.root)
            self.assertEqual(pins.tree_sha256(folder), self.spec["tree_sha256"])
            self.assertEqual(download.call_count, 2)
        with mock.patch.object(weights, "download", side_effect=AssertionError("unexpected network")):
            self.assertEqual(weights.install("fixture", self.root), folder)

    def test_failed_or_changed_download_never_installs_partial_cache(self):
        for failure in (OSError("interrupted"), None):
            def bad_download(repo, revision, relative, destination):
                if failure:
                    raise failure
                destination.write_bytes(b"wrong bytes")
            with self.subTest(failure=failure), mock.patch.object(weights, "download", side_effect=bad_download):
                with self.assertRaises((OSError, ValueError)):
                    weights.install("fixture", self.root)
                self.assertEqual(list(self.root.iterdir()), [])

    def test_changed_existing_cache_is_preserved(self):
        folder = self.root / "fixture"
        folder.mkdir()
        (folder / "keep.txt").write_bytes(b"keep")
        with mock.patch.object(weights, "download", side_effect=AssertionError("unexpected network")):
            with self.assertRaisesRegex(ValueError, "missing or changed"):
                weights.install("fixture", self.root)
        self.assertEqual((folder / "keep.txt").read_bytes(), b"keep")

    def test_manifest_file_hashes_match_the_registered_tree_hashes(self):
        for name, spec in pins.FLUID_MODELS.items():
            with self.subTest(model=name):
                self.assertRegex(spec["revision"], r"^[0-9a-f]{40}$")
                digest = hashlib.sha256("".join(f"{path}\0{sha}\n" for path, sha in sorted(spec["files"].items())).encode()).hexdigest()
                self.assertEqual(digest, spec["tree_sha256"])


class SetupPreflight(unittest.TestCase):
    def test_missing_large_asr_stops_preflight_offline(self):
        with mock.patch.object(pins, "snapshot", side_effect=FileNotFoundError) as snapshot, \
                mock.patch.object(pins, "check_weights") as check, contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(recap.main(["preflight", "--asr", "all"]), 1)
        self.assertIn("setup --asr all", errors.getvalue())
        snapshot.assert_called_once_with(*pins.ASR_MODELS["large-v3"], local_files_only=True)
        check.assert_not_called()

    def test_all_checks_both_asrs_summary_shards_and_diarizer(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for name in ("config.json", "weights.npz", "tokenizer.json", "tokenizer_config.json", "part.safetensors"):
                (folder / name).write_text("fixture")
            (folder / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {"layer": "part.safetensors"}}))
            with mock.patch.object(pins, "snapshot", return_value=str(folder)) as snapshot, \
                    mock.patch.object(pins, "FLUIDAUDIO_CLI", Path(sys.executable)), \
                    mock.patch.object(pins, "check_weights") as check, \
                    mock.patch.object(recap.shutil, "which", return_value="fixture"), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(recap.main(["preflight", "--asr", "all"]), 0)
                self.assertEqual(snapshot.call_count, 3)
                self.assertTrue(all(call.kwargs == {"local_files_only": True} for call in snapshot.call_args_list))
                check.assert_called_once_with("sortformer")
                (folder / "part.safetensors").unlink()
                self.assertEqual(recap.main(["preflight", "--asr", "all"]), 1)
                self.assertIn(pins.SUMMARY_REPO, errors.getvalue())

    def test_setup_all_downloads_both_asrs_and_restores_before_warmup(self):
        events = []
        def fake_run(argv, **kwargs):
            if "sortformer" in argv:
                self.assertIn("restored", events)
                Path(argv[-1]).write_text("{}")
        with mock.patch.object(pins, "snapshot", return_value="cached") as snapshot, \
                mock.patch.object(pins, "FLUIDAUDIO_CLI", Path(sys.executable)), \
                mock.patch.object(weights, "install", side_effect=lambda name: events.append("restored")), \
                mock.patch.object(recap.subprocess, "run", side_effect=fake_run), \
                mock.patch.object(pins, "check_weights"), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(recap.main(["setup", "--asr", "all"]), 0)
        self.assertEqual(snapshot.call_args_list, [mock.call(*pair) for pair in
                         [*pins.ASR_MODELS.values(), (pins.SUMMARY_REPO, pins.SUMMARY_REVISION)]])
