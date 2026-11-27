"""Speak requested turns with LFM3-Audio-2B in this locked MLX-VLM environment.

Usage: uv run --frozen --project experiments/lfm3-audio python tts_render.py request.json out_dir
The request is {"seed": int, "language": "zh"|"en", "turns": [{"index", "gender", "text"}]}.
Each turn is written as out_dir/NNN.wav at 24 kHz, with out_dir/report.json.
"""
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
PINS = json.loads((HERE / "tts_pins.json").read_text())


def load_request(path):
    request = json.loads(path.read_text(encoding="utf-8"))
    seed = request["seed"]
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 2 ** 32:
        raise ValueError("seed must be an integer from 0 through 2**32 - 1")
    if request["language"] not in PINS["languages"]:
        raise ValueError(f"unsupported language: {request['language']}")
    seen = set()
    for turn in request["turns"]:
        index = turn["index"]
        if not isinstance(index, int) or isinstance(index, bool) or index < 0 or index in seen:
            raise ValueError("turn indices must be unique nonnegative integers")
        seen.add(index)
        if turn["gender"] not in ("female", "male"):
            raise ValueError(f"unsupported voice: {turn['gender']}")
        if not isinstance(turn["text"], str) or not turn["text"].strip():
            raise ValueError("turn text must be a nonempty string")
    return request


def render(request, output):
    import mlx.core as mx
    import numpy as np
    import soundfile as sf
    from mlx_vlm import load
    from mlx_vlm.generate.audio import generate_audio
    from mlx_vlm.prompt_utils import apply_chat_template

    settings = dict(PINS["settings"])
    rate = settings.pop("sample_rate")
    settings.pop("turn_seed")
    model, processor = load(PINS["model"]["repository"], revision=PINS["model"]["revision"])
    language = PINS["languages"][request["language"]]
    output.mkdir(parents=True, exist_ok=True)
    report = []
    for turn in request["turns"]:
        system = PINS["prompt"].format(language=language, gender=turn["gender"])
        prompt = apply_chat_template(processor, model.config, [
            {"role": "system", "content": system},
            {"role": "user", "content": turn["text"]}], use_tts_template=True)
        mx.random.seed(request["seed"] + turn["index"])
        started = time.time()
        result = generate_audio(model, processor, prompt, **settings)
        if result.sample_rate != rate:
            raise ValueError(f"expected {rate} Hz speech, got {result.sample_rate}")
        audio = np.array(result.audio, dtype=np.float32).reshape(-1)
        if not audio.size:
            raise ValueError(f"turn {turn['index']} produced no speech")
        sf.write(output / f"{turn['index']:03d}.wav", audio, rate, subtype="FLOAT")
        report.append({"index": turn["index"], "system": system, "seconds": round(audio.size / rate, 3),
                       "finish_reason": result.finish_reason,
                       "elapsed_seconds": round(time.time() - started, 2)})
        print(f"LFM3 turn {turn['index'] + 1} {turn['gender']} {audio.size / rate:.1f}s "
              f"({result.finish_reason})", flush=True)
    report = {"turns": report, "peak_memory_gb": round(mx.get_peak_memory() / 1e9, 2)}
    (output / "report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    render(load_request(Path(sys.argv[1])), Path(sys.argv[2]))
