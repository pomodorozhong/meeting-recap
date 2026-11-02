"""Fetch and verify immutable EmotiVoice code, weights and language resources."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
import tempfile
from urllib.request import urlopen
import zipfile


HERE = Path(__file__).resolve().parent
PIN_PATH = HERE / "pins.json"


def provenance():
    return json.loads(PIN_PATH.read_text(encoding="utf-8"))


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def relative_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"invalid pinned asset path: {name}")
    return Path(*path.parts)


def verify_files(folder, files, *, exact=False):
    if folder.is_symlink():
        raise ValueError(f"asset directory must not be a symlink: {folder}")
    for name, expected in files.items():
        path = folder / relative_path(name)
        if (not path.is_file() or (exact and path.is_symlink())
                or digest(path) != expected):
            raise ValueError(f"EmotiVoice asset hash differs: {name}")
    if exact:
        actual = {str(path.relative_to(folder)) for path in folder.rglob("*")
                  if path.is_file() and "__pycache__" not in path.parts}
        if actual != set(files):
            raise ValueError(f"unexpected files in pinned asset directory: {folder.name}")


def download(url, destination, expected):
    with urlopen(url, timeout=90) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    if digest(destination) != expected:
        raise ValueError(f"downloaded asset hash differs: {destination.name}")


@contextmanager
def preparation_lock(cache):
    """Serialize atomic directory publication across concurrent render processes."""
    with (cache / ".prepare.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def code_snapshot(cache, pin):
    target = cache / ("code-" + pin["revision"])
    if target.exists():
        verify_files(target, pin["files"], exact=True)
        return target
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        temporary = Path(temporary)
        archive = temporary / "source.tar.gz"
        download(pin["archive_url"], archive, pin["archive_sha256"])
        staged = temporary / "source"
        staged.mkdir()
        with tarfile.open(archive, "r:gz") as bundle:
            for name in pin["files"]:
                relative = relative_path(name)
                member = bundle.getmember(pin["archive_root"] + "/" + name)
                if not member.isfile() or member.size > 64 * 1024 * 1024:
                    raise ValueError(f"invalid source archive member: {name}")
                destination = staged / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source:
                    destination.write_bytes(source.read())
        verify_files(staged, pin["files"], exact=True)
        os.replace(staged, target)
    return target


def nltk_snapshot(cache, pin):
    target = cache / ("nltk-" + pin["revision"])
    expected = {}
    for resource in pin["resources"]:
        archive_name = resource["archive_url"].rsplit("/", 1)[1]
        expected[resource["destination"] + "/" + archive_name] = resource["archive_sha256"]
        expected.update(resource["files"])
    if target.exists():
        verify_files(target, expected, exact=True)
        return target
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        staged = Path(temporary) / "nltk"
        staged.mkdir()
        for resource in pin["resources"]:
            destination = relative_path(resource["destination"])
            archive_name = resource["archive_url"].rsplit("/", 1)[1]
            archive = staged / destination / archive_name
            archive.parent.mkdir(parents=True, exist_ok=True)
            download(resource["archive_url"], archive, resource["archive_sha256"])
            with zipfile.ZipFile(archive) as bundle:
                for name in resource["files"]:
                    relative = relative_path(name)
                    member = relative.relative_to(destination).as_posix()
                    output = staged / relative
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(bundle.read(member))
        verify_files(staged, expected, exact=True)
        os.replace(staged, target)
    return target


def checked_snapshot(pin):
    from huggingface_hub import snapshot_download

    folder = Path(snapshot_download(repo_id=pin["repository"], revision=pin["revision"],
                                    allow_patterns=list(pin["files"])))
    verify_files(folder, pin["files"])
    return folder


def prepare_assets():
    from huggingface_hub.constants import HF_HUB_CACHE

    pin = provenance()
    cache = Path(HF_HUB_CACHE) / "meeting-recap-emotivoice"
    cache.mkdir(parents=True, exist_ok=True)
    with preparation_lock(cache):
        source = code_snapshot(cache, pin["code"])
        nltk = nltk_snapshot(cache, pin["resources"])
    return {"code": source, "nltk": nltk,
            **{name: checked_snapshot(asset) for name, asset in pin["artifacts"].items()}}
