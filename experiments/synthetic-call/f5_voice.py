"""Pinned F5-TTS female voice for the synthetic recording collection.

The reference is a published demo clip from the pinned ZipVoice release. All
model files and the reference are checked before inference. Importing this
module and reading provenance never downloads weights or initializes MLX.
"""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import tarfile
import tempfile
from threading import RLock
from urllib.request import urlopen


PIN_PATH = Path(__file__).resolve().parent / "reference/f5-voice.json"
VOICE_ID = "f5-news-female"
RATE = 24000
# MLX's RNG function is process-global, so serialize its scoped compatibility fix.
SAMPLING_LOCK = RLock()


def provenance():
    """Return the committed voice configuration without loading the model."""
    pin = json.loads(PIN_PATH.read_text(encoding="utf-8"))
    pin["models"] = {asset["repository"]: asset["revision"] for asset in pin["artifacts"].values()}
    return pin


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def checked_snapshot(pin):
    from huggingface_hub import snapshot_download

    folder = Path(snapshot_download(
        repo_id=pin["repository"], revision=pin["revision"],
        allow_patterns=list(pin["files"]),
    ))
    for name, expected in pin["files"].items():
        if digest(folder / name) != expected:
            raise ValueError(f"F5 asset hash differs: {pin['repository']}/{name}")
    return folder


def reference_path(pin):
    """Download a verified archive and publish only its verified reference WAV."""
    from huggingface_hub.constants import HF_HUB_CACHE

    cache = Path(HF_HUB_CACHE) / "meeting-recap-f5"
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / f"{pin['sha256']}.wav"
    if target.exists():
        if digest(target) != pin["sha256"]:
            raise ValueError("F5 reference hash differs from the pinned female voice")
        return target
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        archive = Path(temporary) / "reference.tar.bz2"
        with urlopen(pin["archive_url"], timeout=60) as source, archive.open("wb") as output:
            while chunk := source.read(1024 * 1024):
                output.write(chunk)
        if digest(archive) != pin["archive_sha256"]:
            raise ValueError("F5 reference archive hash differs from the pin")
        with tarfile.open(archive, "r:bz2") as bundle:
            member = bundle.getmember(pin["member"])
            if not member.isfile() or member.size > 10 * 1024 * 1024:
                raise ValueError("F5 reference archive member is not a small regular file")
            with bundle.extractfile(member) as source:
                reference = Path(temporary) / "reference.wav"
                reference.write_bytes(source.read())
        if digest(reference) != pin["sha256"]:
            raise ValueError("F5 reference WAV hash differs from the pin")
        os.replace(reference, target)
    return target


@contextmanager
def integer_rng_shapes(mx):
    """Adapt F5 0.2.6's scalar shape values to MLX 0.32's integer API."""
    with SAMPLING_LOCK:
        original = mx.random.normal

        def normal(shape=(), **kwargs):
            return original(tuple(int(dimension) for dimension in shape), **kwargs)

        mx.random.normal = normal
        try:
            yield
        finally:
            mx.random.normal = original


class F5Voice:
    """Load the approved reference and synthesis models on first use."""

    def __init__(self):
        self._pin = provenance()
        self._model = None
        self._reference = None
        self._simplify = None

    def provenance(self):
        return provenance()

    def _load(self):
        import mlx.core as mx
        import mlx.nn as nn
        import soundfile as sf
        from f5_tts_mlx.cfm import F5TTS
        from f5_tts_mlx.dit import DiT
        from opencc import OpenCC
        from vocos_mlx import Vocos

        model_path = checked_snapshot(self._pin["artifacts"]["tts"])
        vocoder_path = checked_snapshot(self._pin["artifacts"]["vocoder"])
        reference = reference_path(self._pin["reference"])
        audio, rate = sf.read(reference, dtype="float32")
        if rate != RATE or audio.ndim != 1:
            raise ValueError("F5 reference must be 24 kHz mono")
        reference_audio = mx.array(audio)
        rms = mx.sqrt(mx.mean(mx.square(reference_audio)))
        if float(rms) < 0.1:
            reference_audio = reference_audio * 0.1 / rms
        vocab = {character: index for index, character in enumerate(
            (model_path / "vocab.txt").read_text(encoding="utf-8").split("\n"))}
        vocoder = Vocos.from_pretrained(str(vocoder_path))
        # Match f5-tts-mlx 0.2.6's v1 architecture and quantization exactly.
        # Automatic duration prediction is unused because every turn supplies it.
        model = F5TTS(
            transformer=DiT(dim=1024, depth=22, heads=16, ff_mult=2,
                            text_dim=512, conv_layers=4,
                            text_num_embeds=len(vocab) - 1, text_mask_padding=True),
            vocab_char_map=vocab, vocoder=vocoder.decode,
        )
        nn.quantize(model, bits=self._pin["settings"]["quantization_bits"], class_predicate=lambda path, layer:
                    isinstance(layer, nn.Linear) and layer.weight.shape[1] % 64 == 0)
        model.load_weights(list(mx.load(str(model_path / "model_v1_4b.safetensors")).items()))
        mx.eval(model.parameters(), reference_audio)
        self._model = model
        self._reference = reference_audio
        self._simplify = OpenCC("t2s")

    def generate(self, text, duration_seconds, seed=7):
        """Return native float32 audio and its sample rate for one scripted turn."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("F5 text must be a nonempty string")
        if (isinstance(duration_seconds, bool) or not isinstance(duration_seconds, (int, float))
                or not math.isfinite(duration_seconds) or duration_seconds <= 0):
            raise ValueError("F5 duration_seconds must be a positive finite number")
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            raise ValueError("F5 seed must be a nonnegative integer")
        import mlx.core as mx
        import numpy as np
        from f5_tts_mlx.utils import convert_char_to_pinyin

        with SAMPLING_LOCK:
            if self._model is None:
                self._load()
            duration_frames = int(len(self._reference) / 256 + duration_seconds * RATE / 256)
            if duration_frames > 4096:
                raise ValueError("F5 turn plus reference exceeds the 4096-frame model limit")
            prompt = convert_char_to_pinyin([
                self._pin["reference"]["text"] + " " + self._simplify.convert(text)])
            mx.random.seed(seed)
            settings = self._pin["settings"]
            with integer_rng_shapes(mx):
                result, _ = self._model.sample(
                    self._reference[None, :], text=prompt, duration=duration_frames, seed=seed,
                    steps=settings["steps"], method=settings["method"],
                    cfg_strength=settings["cfg_strength"], speed=settings["speed"],
                    sway_sampling_coef=settings["sway_sampling_coef"],
                )
                result = result[len(self._reference):]
                mx.eval(result)
            audio = np.asarray(result.astype(mx.float32)).reshape(-1)
            mx.clear_cache()
        if (len(audio) < RATE // 2 or not np.isfinite(audio).all()
                or float(np.max(np.abs(audio))) < 0.002):
            raise ValueError("F5 produced an unusable turn")
        return audio, RATE
