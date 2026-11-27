"""Transcribe the synthetic collection's fourteen scripted calls with LFM3-Audio-2B (#27).

Usage: uv run --frozen --project experiments/lfm3-audio python experiments/lfm3-audio/run.py
           FIXTURES RUNS --prompt declared|auto
FIXTURES is the verified collection from experiments/synthetic-call/collection.py. Each call
is written to RUNS/<call>/asr.json, in the shape score_transcripts.py reads. Calls whose report
already exists are skipped. LFM3 stops early on long audio, so each call is cut into windows of
at most 30 s, at the quietest 0.1 s of the last 5 s of each window (from the audio alone).
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
SYNTHETIC = HERE.parent / "synthetic-call"
MODEL = {"repository": "LiquidAI/LFM3-Audio-2B-MLX-bf16",
         "revision": "452469a1afe66dd4932d0e9237603229fa606c0d"}
LANGUAGES = {"zh": "Chinese", "en": "English"}
PROMPTS = {"declared": "Perform ASR in {language}.", "auto": "Perform ASR."}
RATE, WINDOW, SEARCH, FRAME = 16000, 30.0, 5.0, 0.1
SETTINGS = {"temperature": 0.0, "max_tokens": 1024, "window_seconds": WINDOW,
            "cut_search_seconds": SEARCH, "cut_frame_seconds": FRAME}
# The same order and folders as experiments/synthetic-call/collection.py.
SCRIPTS = {"script": "script.json", **{name: f"scripts/{name}.json" for name in (
    "handoff", "logistics", "stocktake", "scheduling", "design", "onboarding", "localization",
    "english-audit", "english-handoff", "english-design", "english-tabletop",
    "english-committee", "english-training")}}


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify(fixtures):
    """Refuse a fixture folder whose audio or scripts differ from the committed hashes."""
    expected = json.loads((SYNTHETIC / "reference/collection-sha256.json").read_text())
    for name, script in SCRIPTS.items():
        if digest(fixtures / name / "call.wav") != expected[name]["call.wav"]:
            raise ValueError(f"{name}/call.wav differs from the collection hashes")
        if digest(SYNTHETIC / script) != expected[name]["script_sha256"]:
            raise ValueError(f"{script} differs from the collection hashes")


def windows(audio):
    """Split points in samples: each window ends at its quietest frame near 30 s."""
    import numpy as np

    window, search, frame = (round(x * RATE) for x in (WINDOW, SEARCH, FRAME))
    cuts, start = [], 0
    while len(audio) - start > window:
        low = start + window - search
        frames = audio[low:start + window][: search // frame * frame].reshape(-1, frame)
        quietest = int(np.argmin((frames ** 2).mean(1)))
        start = low + quietest * frame + frame // 2
        cuts.append(start)
    return [0, *cuts, len(audio)]


def transcribe(fixtures, runs, prompt_id):
    verify(fixtures)
    pending = [name for name in SCRIPTS if not (runs / name / "asr.json").exists()]
    if not pending:
        print("every call already has a report")
        return
    import mlx.core as mx
    import soundfile as sf
    from mlx_vlm import generate, load
    from mlx_vlm.prompt_utils import apply_chat_template

    started = time.monotonic()
    model, processor = load(MODEL["repository"], revision=MODEL["revision"])
    load_seconds = round(time.monotonic() - started, 2)
    for name in pending:
        script = json.loads((SYNTHETIC / SCRIPTS[name]).read_text())
        language = script.get("language", "zh")
        system = PROMPTS[prompt_id].format(language=LANGUAGES[language])
        prompt = apply_chat_template(processor, model.config, [
            {"role": "system", "content": system}, {"role": "user", "content": ""}], num_audios=1)
        audio, rate = sf.read(fixtures / name / "call.wav", dtype="float32")
        if rate != RATE or audio.ndim != 1:
            raise ValueError(f"{name}: expected 16 kHz mono")
        bounds = windows(audio)
        segments, started = [], time.monotonic()
        for begin, end in zip(bounds, bounds[1:]):
            result = generate(model, processor, prompt, audio=[audio[begin:end]],
                              max_tokens=SETTINGS["max_tokens"], temperature=SETTINGS["temperature"])
            segments.append({"start": round(begin / RATE, 3), "end": round(end / RATE, 3),
                             "text": result.text.strip(), "finish_reason": result.finish_reason})
        elapsed = round(time.monotonic() - started, 2)
        joiner = " " if language == "en" else ""
        report = {"text": joiner.join(s["text"] for s in segments), "segments": segments,
                  "audio_sha256": digest(fixtures / name / "call.wav"),
                  "script_sha256": digest(SYNTHETIC / SCRIPTS[name]), "model": MODEL,
                  "settings": {**SETTINGS, "prompt_id": prompt_id, "system_prompt": system},
                  "audio_seconds": round(len(audio) / RATE, 3), "elapsed_seconds": elapsed,
                  "model_load_seconds": load_seconds,
                  "peak_memory_gb": round(mx.get_peak_memory() / 1e9, 2)}
        (runs / name).mkdir(parents=True, exist_ok=True)
        (runs / name / "asr.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
        stopped = sum(s["finish_reason"] != "stop" for s in segments)
        print(f"{name}: {len(segments)} windows in {elapsed:.1f}s"
              + (f", {stopped} hit the token limit" if stopped else ""), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("fixtures", type=Path, metavar="FIXTURES")
    parser.add_argument("runs", type=Path, metavar="RUNS")
    parser.add_argument("--prompt", choices=PROMPTS, required=True)
    args = parser.parse_args()
    transcribe(args.fixtures, args.runs, args.prompt)


if __name__ == "__main__":
    main()
