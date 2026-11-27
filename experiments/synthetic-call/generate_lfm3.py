"""Re-voice the existing collection scripts with LFM3-Audio-2B, for comparison with the old voices.

Usage: uv run generate_lfm3.py OUT [name ...] [--seed 7]
Writes OUT/<name>/ for each named collection script (all fourteen by default), in the same
layout as generate.py. The scripts, turn order, gaps, levelling and mixing stay the same;
only the voices change. LFM3 offers one female and one male voice per language, so each
speaker gets the gender of their old voice, and same-gender speakers in a call share a voice.
These recordings are for comparing voices only; they are not part of the hashed collection.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from collection import SCRIPTS
from generate import RATE, assemble, level

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent / "lfm3-audio"


def provenance():
    """Read the LFM3 pins and runtime lock hash without loading the model."""
    pin = json.loads((PROJECT / "tts_pins.json").read_text())
    pin["uv_lock_sha256"] = hashlib.sha256((PROJECT / "uv.lock").read_bytes()).hexdigest()
    return pin


def lfm3_voices(speakers, pin):
    """Map each speaker's old voice to the LFM3 gender voice that replaces it."""
    unknown = {s["voice"] for s in speakers.values()} - set(pin["voices"])
    if unknown:
        raise ValueError(f"no LFM3 voice for old voices: {sorted(unknown)}")
    return {speaker: pin["voices"][s["voice"]] for speaker, s in speakers.items()}


def generate(script_path, out, seed=7):
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    script = json.loads(script_path.read_text())
    speakers, turns = script["speakers"], script["turns"]
    language = script.get("language", "zh")
    pin = provenance()
    voices = lfm3_voices(speakers, pin)
    request = {"seed": seed, "language": language, "turns": [
        {"index": i, "gender": voices[turn["speaker"]], "text": turn["text"]}
        for i, turn in enumerate(turns)]}
    (out / "turns").mkdir(parents=True, exist_ok=True)
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="synthetic-lfm3-") as temporary:
        root = Path(temporary)
        (root / "request.json").write_text(json.dumps(request, ensure_ascii=False))
        subprocess.run(["uv", "run", "--frozen", "--project", str(PROJECT), "python",
                        str(PROJECT / "tts_render.py"), str(root / "request.json"), str(root / "audio")],
                       check=True, env={k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"})
        report = json.loads((root / "audio" / "report.json").read_text())
        clips = []
        for i, turn in enumerate(turns):
            audio, rate = sf.read(root / "audio" / f"{i:03d}.wav", dtype="float32")
            clips.append(level(resample_poly(audio, RATE, rate).astype(np.float32)))
            sf.write(out / "turns" / f"{i + 1:02d}-{turn['speaker']}.wav", clips[-1], RATE)
    elapsed = time.time() - started
    (out / "lfm3-report.json").write_text(json.dumps(report, indent=1))
    truncated = [t["index"] + 1 for t in report["turns"] if t["finish_reason"] != "stop"]
    if truncated:
        print(f"warning: turns {truncated} hit the token limit before ending", flush=True)
    assemble(out, turns, clips, {
        "script": script_path.name, "engine": "lfm3",
        "model": {pin["model"]["repository"]: pin["model"]["revision"]},
        "voice_config": {"lfm3": pin}, "language": language, "seed": seed,
        "speakers": speakers, "lfm3_voices": voices,
        "peak_memory_gb": report["peak_memory_gb"]}, elapsed)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("names", nargs="*", choices=[[], *SCRIPTS], metavar="name",
                        help=f"collection scripts to voice (default: all): {', '.join(SCRIPTS)}")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    for name in args.names or SCRIPTS:
        target = args.out / name
        if (target / "manifest.json").exists():
            print(f"{name}: already generated, skipping", flush=True)
            continue
        print(f"{name}: voicing {SCRIPTS[name].name} with LFM3", flush=True)
        generate(SCRIPTS[name], target, args.seed)


if __name__ == "__main__":
    main()
