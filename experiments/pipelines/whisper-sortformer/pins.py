"""Pinned models, and loading an exact Hugging Face snapshot."""
from pathlib import Path

WHISPER_REPO = "mlx-community/whisper-large-v3-mlx"
WHISPER_REVISION = "49e6aa286ad60c14352c404340ded53710378a11"
SUMMARY_REPO = "mlx-community/Qwen3.5-9B-4bit"
SUMMARY_REVISION = "8b2b98c00a6b4d291155e4890773ca8f769aee53"
FLUIDAUDIO_REVISION = "ea500621819cadc46d6212af44624f2b45ab3240"
FLUIDAUDIO_CLI = Path(__file__).resolve().parent / ".build" / "release" / "fluidaudiocli"
# Who: the SDK revision pins the weights (desert-ant-labs/who v0.3.4, Core ML int8).
WHO_SDK_REVISION = "1a5efed67f44731b5eb5433aa9be3eebae05e269"
WHO_WEIGHTS = "desert-ant-labs/who v0.3.4 coreml-int8"
WHO_CLI = Path(__file__).resolve().parent / ".build" / "release" / "who-diarize"


def who_models():
    """The Who weights folder, outside the checkout; WHO_MODELS overrides the default."""
    import os

    return Path(os.environ.get("WHO_MODELS") or Path.home() / "Library/Application Support/meeting-recap/who")


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
