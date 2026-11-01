"""Pinned models, and loading an exact Hugging Face snapshot."""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
WHISPER_REPO = "mlx-community/whisper-large-v3-mlx"
WHISPER_REVISION = "49e6aa286ad60c14352c404340ded53710378a11"
SUMMARY_REPO = "mlx-community/Qwen3.5-9B-4bit"
SUMMARY_REVISION = "8b2b98c00a6b4d291155e4890773ca8f769aee53"


def swift_revision(identity):
    """A Swift dependency's revision, from Package.resolved, so the pin is written down in one place."""
    pins = json.loads((HERE / "Package.resolved").read_text())["pins"]
    return next(pin["state"]["revision"] for pin in pins if pin["identity"] == identity)


FLUIDAUDIO_REVISION = swift_revision("fluidaudio")
FLUIDAUDIO_CLI = HERE / ".build" / "release" / "fluidaudiocli"
# FluidAudio downloads Sortformer's weights from its model repo's main branch, not a revision, so the
# downloaded files are pinned by digest instead: these are the files the 2026-11-01 baseline ran with.
SORTFORMER_MODELS = Path.home() / "Library/Application Support/FluidAudio/Models/sortformer"
SORTFORMER_SHA256 = "a5cb7e5cdab78f6c0e5deb5dd56783445b72d2a9400f8fdf2611d2c78882e665"
# Who: the SDK revision names the weights (desert-ant-labs/who v0.3.4, Core ML int8), and the digest pins them.
WHO_SDK_REVISION = swift_revision("desert-ant-core")
WHO_WEIGHTS = "desert-ant-labs/who v0.3.4 coreml-int8"
WHO_SHA256 = "b19f4740c7b295686b73fd70c9f9e7fce48f68ac6e996864c128464685cf859f"
WHO_CLI = HERE / ".build" / "release" / "who-diarize"


def who_models():
    """The Who weights folder, outside the checkout; WHO_MODELS overrides the default."""
    return Path(os.environ.get("WHO_MODELS") or Path.home() / "Library/Application Support/meeting-recap/who")


def tree_sha256(folder):
    """One SHA-256 over every file under `folder`: each relative path and its file's SHA-256, in path order."""
    digest = hashlib.sha256()
    for path in sorted(p for p in Path(folder).rglob("*") if p.is_file()):
        file_digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                file_digest.update(block)
        digest.update(f"{path.relative_to(folder).as_posix()}\0{file_digest.hexdigest()}\n".encode())
    return digest.hexdigest()


def diarizer_weights(diarizer):
    """The weights folder a diarizer loads, and the digest it must have."""
    if diarizer == "who":
        return who_models() / "coreml-int8", WHO_SHA256
    return SORTFORMER_MODELS, SORTFORMER_SHA256


def check_weights(diarizer):
    """Refuse weights that are missing or differ from the pinned ones; returns their digest."""
    folder, expected = diarizer_weights(diarizer)
    if not folder.is_dir():
        setup = "recap.py setup --who" if diarizer == "who" else "recap.py setup"
        raise ValueError(f"no {diarizer} weights in {folder}; run `{setup}` first")
    actual = tree_sha256(folder)
    if actual != expected:
        raise ValueError(f"the {diarizer} weights in {folder} have SHA-256 {actual}, not the pinned {expected}; "
                         "they may have been updated upstream. Remove the folder and rerun setup, and if the "
                         "digest still differs, the pin needs a new baseline")
    return actual


def snapshot(repo, revision):
    """Local path of the exact revision; with HF_HUB_OFFLINE=1 it must already be cached."""
    from huggingface_hub import snapshot_download

    path = snapshot_download(repo_id=repo, revision=revision)
    if Path(path).name != revision:
        raise ValueError(f"{repo} snapshot {Path(path).name} does not match the pinned revision {revision}")
    return path


def mlx_peak_bytes():
    import mlx.core as mx

    peak = getattr(mx, "get_peak_memory", None) or mx.metal.get_peak_memory
    return int(peak())
