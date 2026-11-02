"""Pinned EmotiVoice assets reject corruption and retain required language ZIPs."""
from hashlib import sha256
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile


HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
from emotivoice import assets


def archive_payload(name, payload, *, symlink=False):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as bundle:
        member = tarfile.TarInfo("source/" + name)
        if symlink:
            member.type = tarfile.SYMTYPE
            member.linkname = "../../outside.py"
            bundle.addfile(member)
        else:
            member.size = len(payload)
            bundle.addfile(member, io.BytesIO(payload))
    return buffer.getvalue()


class PinnedEmotiAssets(unittest.TestCase):
    def test_cached_source_corruption_is_rejected_and_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            folder = cache / "code-revision"
            folder.mkdir()
            (folder / "frontend.py").write_bytes(b"changed")
            pin = {"revision": "revision", "files": {"frontend.py": sha256(b"expected").hexdigest()}}
            with mock.patch.object(assets, "download") as download:
                with self.assertRaisesRegex(ValueError, "frontend.py"):
                    assets.code_snapshot(cache, pin)
                download.assert_not_called()
            self.assertEqual((folder / "frontend.py").read_bytes(), b"changed")

    def test_source_archive_checks_member_type_and_publishes_verified_files(self):
        for symlink in (False, True):
            with self.subTest(symlink=symlink), tempfile.TemporaryDirectory() as temporary:
                archive = archive_payload("frontend.py", b"expected", symlink=symlink)
                pin = {"revision": "revision", "archive_root": "source", "archive_url": "https://example.invalid/source.tar.gz",
                       "archive_sha256": sha256(archive).hexdigest(),
                       "files": {"frontend.py": sha256(b"expected").hexdigest()}}
                with mock.patch.object(assets, "urlopen", return_value=io.BytesIO(archive)):
                    if symlink:
                        with self.assertRaisesRegex(ValueError, "archive member"):
                            assets.code_snapshot(Path(temporary), pin)
                        self.assertFalse((Path(temporary) / "code-revision").exists())
                    else:
                        folder = assets.code_snapshot(Path(temporary), pin)
                        self.assertEqual((folder / "frontend.py").read_bytes(), b"expected")

    def test_nltk_snapshot_keeps_zip_and_rejects_changed_extracted_resource(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as bundle:
            bundle.writestr("cmudict/cmudict", b"dictionary")
        archive = buffer.getvalue()
        pin = {"revision": "revision", "resources": [{
            "archive_url": "https://example.invalid/cmudict.zip",
            "archive_sha256": sha256(archive).hexdigest(), "destination": "corpora",
            "files": {"corpora/cmudict/cmudict": sha256(b"dictionary").hexdigest()}}]}
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(assets, "urlopen", return_value=io.BytesIO(archive)):
                folder = assets.nltk_snapshot(Path(temporary), pin)
            self.assertEqual((folder / "corpora/cmudict.zip").read_bytes(), archive)
            resource = folder / "corpora/cmudict/cmudict"
            resource.write_bytes(b"changed")
            with mock.patch.object(assets, "download") as download:
                with self.assertRaisesRegex(ValueError, "cmudict"):
                    assets.nltk_snapshot(Path(temporary), pin)
                download.assert_not_called()
            self.assertEqual(resource.read_bytes(), b"changed")

    def test_wrong_download_digest_does_not_publish_a_source_directory(self):
        pin = {"revision": "revision", "archive_root": "source", "archive_url": "https://example.invalid/source.tar.gz",
               "archive_sha256": sha256(b"expected").hexdigest(), "files": {}}
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(assets, "urlopen", return_value=io.BytesIO(b"changed")):
                with self.assertRaisesRegex(ValueError, "downloaded asset hash"):
                    assets.code_snapshot(Path(temporary), pin)
            self.assertFalse((Path(temporary) / "code-revision").exists())
