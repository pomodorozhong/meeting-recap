"""Reject altered F5 assets and preserve scoped runtime compatibility changes."""
import hashlib
import io
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import wave

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
import f5_voice as f5


def reference_bundle(*, symlink=False):
    """A generated silent WAV in an archive, with the same pin shape as F5."""
    audio = io.BytesIO()
    with wave.open(audio, "wb") as output:
        output.setparams((1, 2, 24000, 24, "NONE", "not compressed"))
        output.writeframes(b"\0\0" * 24)
    payload = audio.getvalue()
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:bz2") as output:
        entry = tarfile.TarInfo("test_wavs/news-female.wav")
        if symlink:
            entry.type = tarfile.SYMTYPE
            entry.linkname = "outside.wav"
            output.addfile(entry)
        else:
            entry.size = len(payload)
            output.addfile(entry, io.BytesIO(payload))
    archive_bytes = archive.getvalue()
    return archive_bytes, payload, {
        "archive_url": "https://example.invalid/reference.tar.bz2",
        "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
        "member": entry.name,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


class F5Pins(unittest.TestCase):
    def test_provenance_and_lazy_construction_do_not_import_inference_libraries(self):
        import subprocess
        snippet = (
            "import sys;sys.path.insert(0,sys.argv[1]);import f5_voice;"
            "voice=f5_voice.F5Voice();assert voice._model is None;"
            "assert f5_voice.provenance()['voice']==f5_voice.VOICE_ID;"
            "assert not {'mlx','numpy','f5_tts_mlx','huggingface_hub'} & sys.modules.keys()"
        )
        subprocess.run([sys.executable, "-I", "-c", snippet, str(HERE)], check=True)

    def test_changed_model_weight_is_rejected(self):
        import huggingface_hub
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            weight = folder / "model.safetensors"
            weight.write_bytes(b"pinned weight")
            pin = {"repository": "test/model", "revision": "a" * 40,
                   "files": {weight.name: f5.digest(weight)}}
            with mock.patch.object(huggingface_hub, "snapshot_download", return_value=str(folder)):
                self.assertEqual(f5.checked_snapshot(pin), folder)
                weight.write_bytes(b"altered weight")
                with self.assertRaisesRegex(ValueError, "F5 asset hash differs"):
                    f5.checked_snapshot(pin)
            self.assertEqual(weight.read_bytes(), b"altered weight")

    def test_reference_verifies_archive_and_wav_and_preserves_corrupted_cache(self):
        from huggingface_hub import constants
        archive, payload, pin = reference_bundle()
        with tempfile.TemporaryDirectory() as temporary, \
                mock.patch.object(constants, "HF_HUB_CACHE", temporary), \
                mock.patch.object(f5, "urlopen", return_value=io.BytesIO(archive)) as download:
            reference = f5.reference_path(pin)
            self.assertEqual(reference.read_bytes(), payload)
            self.assertEqual(f5.reference_path(pin), reference)
            self.assertEqual(download.call_count, 1)
            reference.write_bytes(b"altered reference")
            with self.assertRaisesRegex(ValueError, "reference hash differs"):
                f5.reference_path(pin)
            self.assertEqual(download.call_count, 1)
            self.assertEqual(reference.read_bytes(), b"altered reference")

    def test_archive_member_must_be_regular_and_both_hashes_must_match(self):
        from huggingface_hub import constants
        for changed in ("archive", "wav", "symlink"):
            with self.subTest(changed=changed):
                archive, _, pin = reference_bundle(symlink=changed == "symlink")
                if changed == "archive":
                    pin["archive_sha256"] = "0" * 64
                if changed == "wav":
                    pin["sha256"] = "0" * 64
                with tempfile.TemporaryDirectory() as temporary, \
                        mock.patch.object(constants, "HF_HUB_CACHE", temporary), \
                        mock.patch.object(f5, "urlopen", return_value=io.BytesIO(archive)):
                    with self.assertRaises(ValueError):
                        f5.reference_path(pin)
                    self.assertEqual(list((Path(temporary) / "meeting-recap-f5").iterdir()), [])

    def test_integer_rng_adapter_restores_original_even_on_failure(self):
        observed = []

        def original(shape):
            observed.append(shape)

        runtime = SimpleNamespace(random=SimpleNamespace(normal=original))
        with self.assertRaisesRegex(RuntimeError, "failed sample"):
            with f5.integer_rng_shapes(runtime):
                runtime.random.normal((3, 4.0))
                raise RuntimeError("failed sample")
        self.assertEqual(observed, [(3, 4)])
        self.assertIs(runtime.random.normal, original)

    def test_invalid_turn_parameters_fail_before_loading_a_model(self):
        voice = f5.F5Voice()
        for text, duration, seed in [("", 2, 7), ("text", float("nan"), 7),
                                     ("text", 0, 7), ("text", True, 7),
                                     ("text", 2, -1), ("text", 2, True)]:
            with self.subTest(text=text, duration=duration, seed=seed), \
                    mock.patch.object(voice, "_load") as load:
                with self.assertRaises(ValueError):
                    voice.generate(text, duration, seed)
                load.assert_not_called()
