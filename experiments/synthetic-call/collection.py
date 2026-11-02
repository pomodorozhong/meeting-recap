"""Build or verify the ten seed-7 synthetic recordings."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

from generate import voice_configuration

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
RATE = 16000
SCRIPTS = {
    "script": HERE / "script.json",
    "handoff": HERE / "scripts/handoff.json",
    "logistics": HERE / "scripts/logistics.json",
    "stocktake": HERE / "scripts/stocktake.json",
    "scheduling": HERE / "scripts/scheduling.json",
    "design": HERE / "scripts/design.json",
    "onboarding": HERE / "scripts/onboarding.json",
}
REFERENCE = HERE / "reference/collection-sha256.json"
PAYLOADS = ("call.wav", "transcript.json", "segments.json")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def samples(path):
    audio, rate = sf.read(path, dtype="float32")
    if rate != RATE or audio.ndim != 1:
        raise ValueError(f"expected 16 kHz mono: {path}")
    return audio


def channel(source, segments):
    """Attenuate B by 14 dB, then add seeded stationary noise at -42 dBFS RMS."""
    audio = samples(source / "call.wav")
    for seg in segments:
        if seg["speaker_id"] == "B":
            start, end = (round(seg[key] * RATE) for key in ("start_seconds", "end_seconds"))
            audio[start:end] *= 10 ** (-14 / 20)
    audio += np.random.default_rng(7).normal(0, 10 ** (-42 / 20), len(audio)).astype("float32")
    return audio, segments


def overlap(source, segments):
    """Advance every second handoff by up to 1 s, capped at half of either turn."""
    clean = samples(source / "call.wav")
    pieces, shifted = [], []
    end = 0
    for i, seg in enumerate(segments):
        a, b = (round(seg[key] * RATE) for key in ("start_seconds", "end_seconds"))
        piece = clean[a:b]
        start = RATE // 2 if not i else end + round(0.3 * RATE)
        if i % 2:
            start = end - min(RATE, len(pieces[-1][1]) // 2, len(piece) // 2)
        pieces.append((start, piece))
        end = start + len(piece)
        shifted.append(dict(seg, start_seconds=start / RATE, end_seconds=end / RATE))
    audio = np.zeros(end + RATE // 2, dtype="float32")
    for start, piece in pieces:
        audio[start:start + len(piece)] += piece
    return audio, shifted


CONTROLS = {"handoff-channel": ("handoff", channel), "logistics-overlap": ("logistics", overlap),
            "silence": (None, None)}


def write_control(root, name, out):
    parent, transform = CONTROLS[name]
    manifest = {"condition": name}
    segments, turns = [], []
    if parent is None:
        audio = np.zeros(12 * RATE, dtype="float32")
    else:
        source = root / parent
        manifest["parent_call_sha256"] = digest(source / "call.wav")
        audio, segments = transform(source, load(source / "segments.json"))
        for turn, seg in zip(load(source / "transcript.json")["segments"], segments, strict=True):
            turns.append(dict(turn, start=seg["start_seconds"], end=seg["end_seconds"]))
    out.mkdir()
    audio *= min(1, 0.999 / max(1e-9, float(np.abs(audio).max())))
    sf.write(out / "call.wav", audio, RATE, subtype="PCM_16")
    manifest.update(duration_seconds=len(audio) / RATE, call_sha256=digest(out / "call.wav"))
    transcript = {"segments": turns, "text": "".join(t["text"] for t in turns)}
    for file, data in (("manifest", manifest), ("segments", segments), ("transcript", transcript)):
        (out / f"{file}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def verify(folder, name, reference):
    """Check exact audio and references, plus provenance. Elapsed time is machine-specific."""
    expected = reference[name]
    for file in PAYLOADS:
        if digest(folder / file) != expected[file]:
            raise ValueError(f"{name}/{file} differs from the reference collection")
    fields = {"call_sha256": expected["call.wav"]}
    if name in SCRIPTS:
        script = SCRIPTS[name]
        speakers = load(script)["speakers"]
        fields.update(script=script.name, speakers=speakers, seed=7, **voice_configuration(speakers))
    else:
        fields["condition"] = name
        parent, _ = CONTROLS[name]
        if parent:
            fields["parent_call_sha256"] = reference[parent]["call.wav"]
    manifest = load(folder / "manifest.json")
    duration = manifest.get("duration_seconds")
    if (any(manifest.get(key) != value for key, value in fields.items()) or not isinstance(duration, (int, float))
            or not math.isclose(duration, sf.info(folder / "call.wav").duration, rel_tol=0, abs_tol=0.001)):
        raise ValueError(f"{name}/manifest.json does not describe the reference recording")


def build(root, *, check_only=False):
    reference = load(REFERENCE)
    for name, script in SCRIPTS.items():
        if digest(script) != reference[name]["script_sha256"]:
            raise ValueError(f"{script.name} differs from the reference collection")
    if not check_only:
        root.mkdir(parents=True, exist_ok=True)
    for name in (*SCRIPTS, *CONTROLS):
        target = root / name
        if check_only or target.exists() or target.is_symlink():
            verify(target, name, reference)
            print(f"verified {name}", flush=True)
            continue
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            staged = Path(tmp) / name
            if name in SCRIPTS:
                subprocess.run([sys.executable, HERE / "generate.py", SCRIPTS[name], staged, "7"], check=True)
            else:
                write_control(root, name, staged)
            verify(staged, name, reference)
            staged.rename(target)
        print(f"created {name}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=HERE / "out")
    parser.add_argument("--check", action="store_true", help="verify existing files without generating audio")
    args = parser.parse_args()
    try:
        build(args.root, check_only=args.check)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"{error}\n")
