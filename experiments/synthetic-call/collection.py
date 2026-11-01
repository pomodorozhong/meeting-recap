"""Build the synthetic collection, resuming from existing matching recordings."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
RATE = 16000


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    """Every second handoff starts 1 s early (at most half the previous turn)."""
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


def make(root, name, parent=None):
    target = root / name
    if target.exists():
        raise FileExistsError(f"{target} already exists; use a fresh destination")
    manifest = {"condition": name}
    segments, turns = [], []
    if parent is None:
        audio = np.zeros(12 * RATE, dtype="float32")
    else:
        source = root / parent
        sha = digest(source / "call.wav")
        if sha != load(source / "manifest.json")["call_sha256"]:
            raise ValueError(f"{parent} audio digest mismatch")
        manifest["parent_call_sha256"] = sha
        segments = load(source / "segments.json")
        audio, segments = (channel if name == "handoff-channel" else overlap)(source, segments)
        for turn, seg in zip(load(source / "transcript.json")["segments"], segments, strict=True):
            turns.append(dict(turn, start=seg["start_seconds"], end=seg["end_seconds"]))
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        staged = Path(tmp) / name
        staged.mkdir()
        audio *= min(1, 0.999 / max(1e-9, float(np.abs(audio).max())))
        sf.write(staged / "call.wav", audio, RATE, subtype="PCM_16")
        manifest.update(duration_seconds=len(audio) / RATE, call_sha256=digest(staged / "call.wav"))
        transcript = {"segments": turns, "text": "".join(t["text"] for t in turns)}
        for file, data in (("manifest", manifest), ("segments", segments), ("transcript", transcript)):
            (staged / f"{file}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
        staged.rename(target)
    print(f"{name} {len(audio) / RATE:.2f} s {manifest['call_sha256']}")


def check_clean(target, script):
    plan = load(script)
    manifest = load(target / "manifest.json")
    transcript = load(target / "transcript.json")
    segments = load(target / "segments.json")
    wav = target / "call.wav"
    info = sf.info(wav)
    if (manifest["call_sha256"] != digest(wav) or manifest["model"] != load(HERE / "reference/manifest.json")["model"]
            or manifest["speakers"] != plan["speakers"] or manifest["seed"] != 7
            or (info.samplerate, info.channels, info.subtype) != (RATE, 1, "PCM_16")
            or abs(info.duration - manifest["duration_seconds"]) > 0.001):
        raise ValueError(f"{target} differs from the seed-7 recording; use a fresh destination")
    if transcript["text"] != "".join(t["text"] for t in plan["turns"]):
        raise ValueError(f"{target} has the wrong reference text")
    cursor = 0.0
    for i, (turn, ref, seg) in enumerate(zip(plan["turns"], transcript["segments"], segments, strict=True)):
        start = round(max(0, cursor + turn.get("gap_seconds", 0.3)), 3) if i else 0.5
        end = seg["end_seconds"]
        if (seg["speaker_id"] != turn["speaker"] or seg["start_seconds"] != start or not start < end <= info.duration
                or ref != {"speaker": turn["speaker"], "text": turn["text"], "start": start, "end": end}):
            raise ValueError(f"{target} reference differs at turn {i + 1}")
        cursor = max(cursor, end)


def build(root):
    root.mkdir(parents=True, exist_ok=True)
    scripts = [HERE / "script.json"] + [HERE / "scripts" / f"{name}.json"
                                       for name in ("handoff", "logistics", "stocktake")]
    for script in scripts:
        target = root / script.stem
        if target.exists():
            check_clean(target, script)
            print(f"kept {target.name}", flush=True)
            continue
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            staged = Path(tmp) / script.stem
            subprocess.run([sys.executable, HERE / "generate.py", script, staged, "7"], check=True)
            check_clean(staged, script)
            staged.rename(target)

    for name, parent in (("handoff-channel", "handoff"), ("logistics-overlap", "logistics"), ("silence", None)):
        # Recompute the inexpensive controls and check the references as well as the audio before reuse.
        if not (root / name).exists():
            make(root, name, parent)
            continue
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            check = Path(tmp)
            if parent:
                (check / parent).symlink_to((root / parent).resolve(), target_is_directory=True)
            make(check, name, parent)
            for file in ("manifest.json", "call.wav", "transcript.json", "segments.json"):
                if digest(check / name / file) != digest(root / name / file):
                    raise ValueError(f"{root / name / file} differs; use a fresh destination")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=HERE / "out")
    build(parser.parse_args().root)
