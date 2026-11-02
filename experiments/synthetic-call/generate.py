"""Speak a fictional script with pinned Qwen presets and the F5 female reference.

Usage: uv run generate.py [script.json] [out_dir] [seed]
Defaults are script.json, out/<script name>/ and seed 7. F5 turns supply an
explicit tts_duration_seconds. Output includes audio, timed references and pins.
"""
import hashlib
import json
from pathlib import Path
import sys
import time

from f5_voice import F5Voice, VOICE_ID, provenance

MODEL = ("mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16",
         "52f4770fd9726457eae3d3b6aa92047a25a10776")
RATE, LEVEL = 16000, 0.08
HERE = Path(__file__).resolve().parent


def voice_configuration(speakers):
    """Describe the engines and voice inputs without loading speech models."""
    voices = {speaker["voice"] for speaker in speakers.values()}
    config = {"model": {}}
    if voices - {VOICE_ID}:
        config["model"][MODEL[0]] = MODEL[1]
    if VOICE_ID in voices:
        pin = provenance()
        config["model"].update(pin["models"])
        config["voice_config"] = {VOICE_ID: pin}
    return config


def level(clip):
    import numpy as np

    frames = clip[:len(clip) // 400 * 400].reshape(-1, 400)
    rms = np.sqrt((frames ** 2).mean(1))
    voiced = rms[rms > 0.1 * rms.max()]
    return clip * (LEVEL / max(1e-6, float(np.sqrt((voiced ** 2).mean()))))


def generate(script_path, out, seed=7):
    import mlx.core as mx
    import numpy as np
    import soundfile as sf
    from mlx_audio.tts.utils import load_model
    from scipy.signal import resample_poly

    script = json.loads(script_path.read_text())
    speakers, turns = script["speakers"], script["turns"]
    for turn in turns:
        if speakers[turn["speaker"]]["voice"] == VOICE_ID:
            duration = turn.get("tts_duration_seconds")
            if (isinstance(duration, bool) or not isinstance(duration, (int, float))
                    or not np.isfinite(duration) or duration <= 0):
                raise ValueError("F5 turns require positive tts_duration_seconds")
    config = voice_configuration(speakers)
    (out / "turns").mkdir(parents=True, exist_ok=True)
    started = time.time()
    qwen = load_model(MODEL[0], revision=MODEL[1]) if MODEL[0] in config["model"] else None
    female = F5Voice()
    clips = []
    for i, turn in enumerate(turns):
        voice = speakers[turn["speaker"]]["voice"]
        if voice == VOICE_ID:
            audio, rate = female.generate(turn["text"], turn["tts_duration_seconds"], seed)
        else:
            mx.random.seed(seed + i)
            audio = np.concatenate([np.array(result.audio, dtype=np.float32) for result in
                                    qwen.generate(text=turn["text"], voice=voice, lang_code="chinese")])
            rate = qwen.sample_rate
        clips.append(level(resample_poly(audio, RATE, rate).astype(np.float32)))
        sf.write(out / "turns" / f"{i + 1:02d}-{turn['speaker']}.wav", clips[-1], RATE)
        print(f"{i + 1}/{len(turns)} {turn['speaker']} {len(clips[-1]) / RATE:.1f}s", flush=True)
    elapsed = time.time() - started

    segments, cursor, lead = [], 0.0, 0.5
    for turn, clip in zip(turns, clips):
        start = max(0.0, cursor + turn.get("gap_seconds", 0.3)) if segments else lead
        segments.append({"speaker_id": turn["speaker"], "start_seconds": round(start, 3),
                         "end_seconds": round(start + len(clip) / RATE, 3)})
        cursor = max(cursor, segments[-1]["end_seconds"])
    mix = np.zeros(int((cursor + lead) * RATE), dtype=np.float32)
    for seg, clip in zip(segments, clips):
        start = int(seg["start_seconds"] * RATE)
        mix[start:start + len(clip)] += clip
    mix *= min(1.0, 0.9 / max(1e-9, float(np.abs(mix).max())))
    sf.write(out / "call.wav", mix, RATE, subtype="PCM_16")
    transcript = {"text": "".join(turn["text"] for turn in turns), "segments": [
        {"start": seg["start_seconds"], "end": seg["end_seconds"],
         "text": turn["text"], "speaker": turn["speaker"]} for seg, turn in zip(segments, turns)]}
    manifest = {"script": script_path.name, **config, "seed": seed, "speakers": speakers,
                "duration_seconds": round(len(mix) / RATE, 3), "elapsed_seconds": round(elapsed, 1),
                "call_sha256": hashlib.sha256((out / "call.wav").read_bytes()).hexdigest()}
    for name, payload in (("segments", segments), ("transcript", transcript), ("manifest", manifest)):
        (out / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=name == "segments", indent=1))
    print(f"call.wav {len(mix) / RATE:.1f}s, generated in {elapsed:.0f}s")


if __name__ == "__main__":
    script_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "script.json"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "out" / script_path.stem
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    generate(script_path, out, seed)
