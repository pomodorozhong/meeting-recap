"""Speak a script with Qwen3-TTS CustomVoice's preset speakers, plus its ground truth.

Usage: uv run generate.py [script.json] [out_dir] [seed]   (defaults: script.json, out/<script name>/, 7)
Run it from this folder (or with --project) so uv uses this folder's pyproject.toml and uv.lock.

Each speaker names a preset voice: {"voice": "vivian"}. Writes call.wav (16 kHz mono),
turns/NN-<speaker>.wav, segments.json and transcript.json in the dataset formats, and manifest.json
with every pin. Runs on the GPU through MLX.
"""
import hashlib, json, sys, time
from pathlib import Path

import mlx.core as mx, numpy as np, soundfile as sf
from mlx_audio.tts.utils import load_model
from scipy.signal import resample_poly

MODEL = ("mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16", "52f4770fd9726457eae3d3b6aa92047a25a10776")
RATE, LEVEL = 16000, 0.08  # output rate; RMS of voiced frames each turn is scaled to

here = Path(__file__).resolve().parent
script_path = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "script.json"
script = json.loads(script_path.read_text())
out = Path(sys.argv[2]) if len(sys.argv) > 2 else here / "out" / script_path.stem
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 7


def level(clip):
    frames = clip[:len(clip) // 400 * 400].reshape(-1, 400)
    rms = np.sqrt((frames ** 2).mean(1))
    voiced = rms[rms > 0.1 * rms.max()]
    return clip * (LEVEL / max(1e-6, float(np.sqrt((voiced ** 2).mean()))))


speakers, turns = script["speakers"], script["turns"]
(out / "turns").mkdir(parents=True, exist_ok=True)
t0 = time.time()
model = load_model(MODEL[0], revision=MODEL[1])
clips = []
for i, turn in enumerate(turns):
    mx.random.seed(seed + i)
    audio = np.concatenate([np.array(r.audio, dtype=np.float32) for r in
                            model.generate(text=turn["text"], voice=speakers[turn["speaker"]]["voice"], lang_code="chinese")])
    clips.append(level(resample_poly(audio, RATE, model.sample_rate).astype(np.float32)))
    sf.write(out / "turns" / f"{i + 1:02d}-{turn['speaker']}.wav", clips[-1], RATE)
    print(f"{i + 1}/{len(turns)} {turn['speaker']} {len(clips[-1]) / RATE:.1f}s", flush=True)
elapsed = time.time() - t0

# Lay turns on a timeline: each starts gap_seconds after the previous one ends (negative overlaps it).
segments, cursor, lead = [], 0.0, 0.5
for turn, clip in zip(turns, clips):
    start = max(0.0, cursor + turn.get("gap_seconds", 0.3)) if segments else lead
    segments.append({"speaker_id": turn["speaker"], "start_seconds": round(start, 3),
                     "end_seconds": round(start + len(clip) / RATE, 3)})
    cursor = max(cursor, segments[-1]["end_seconds"])
mix = np.zeros(int((cursor + lead) * RATE), dtype=np.float32)
for seg, clip in zip(segments, clips):
    s = int(seg["start_seconds"] * RATE)
    mix[s:s + len(clip)] += clip
mix *= min(1.0, 0.9 / max(1e-9, float(np.abs(mix).max())))
sf.write(out / "call.wav", mix, RATE, subtype="PCM_16")

json.dump(segments, open(out / "segments.json", "w"), indent=1)
json.dump({"text": "".join(t["text"] for t in turns),
           "segments": [{"start": s["start_seconds"], "end": s["end_seconds"], "text": t["text"], "speaker": t["speaker"]}
                        for s, t in zip(segments, turns)]},
          open(out / "transcript.json", "w"), ensure_ascii=False, indent=1)
json.dump({"script": script_path.name, "model": {MODEL[0]: MODEL[1]}, "seed": seed, "speakers": speakers,
           "duration_seconds": round(len(mix) / RATE, 3), "elapsed_seconds": round(elapsed, 1),
           "call_sha256": hashlib.sha256((out / "call.wav").read_bytes()).hexdigest()},
          open(out / "manifest.json", "w"), ensure_ascii=False, indent=1)
print(f"call.wav {len(mix) / RATE:.1f}s, generated in {elapsed:.0f}s")
