"""ASR stage: Whisper Large v3 through MLX, explicit spoken language, word timestamps, WhisperKit-shaped JSON.

Runs in its own process so the model's memory is released before the next stage.
"""
import json
import sys
import time
import warnings

from pins import ASR_MODELS, mlx_peak_bytes, snapshot


def read_samples(wav):
    from scipy.io import wavfile

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r"Chunk \(non-data\) not understood", category=wavfile.WavFileWarning)
        return wavfile.read(wav, mmap=True)


def digital_silence(samples):
    """Inspect the converted float WAV without rounding away very quiet samples."""
    return bool(samples.size) and all(not samples[i:i + 65536].any() for i in range(0, len(samples), 65536))


def speech_spans(samples, rate):
    """Half-open spans around nonzero samples, splitting only at five full seconds of digital zero."""
    import numpy as np

    minimum, pad = 5 * rate, rate // 4
    first = last = None
    groups = []
    for pos in range(0, len(samples), 65536):
        indices = np.flatnonzero(samples[pos:pos + 65536]) + pos
        if not indices.size:
            continue
        for run in np.split(indices, np.flatnonzero(np.diff(indices) > minimum) + 1):
            a, b = int(run[0]), int(run[-1])
            if first is None or a - last > minimum:
                if first is not None:
                    groups.append((first, last + 1))
                first = a
            last = b
    if first is not None:
        groups.append((first, last + 1))
    return [(0 if a < minimum else a - pad, len(samples) if len(samples) - b < minimum else b + pad)
            for a, b in groups]


def main(wav, out, language="zh", model="large-v3", pause_mode="whole"):
    from pathlib import Path
    import tempfile

    if pause_mode not in ("whole", "split"):
        raise ValueError("pause_mode must be 'whole' or 'split'")
    rate, samples = read_samples(wav)
    if not samples.size:
        raise ValueError("the recording contains no samples")
    if samples.ndim != 1 or rate != 16000:
        raise ValueError("ASR stage expects the pipeline's converted 16 kHz mono WAV")
    whole = [(0, len(samples))]
    if pause_mode == "split":
        spans = speech_spans(samples, rate)
    else:
        spans = [] if digital_silence(samples) else whole
    settings = {"word_timestamps": True, "condition_on_previous_text": False, "digital_pauses": pause_mode}
    if not spans:
        with open(out, "w", encoding="utf-8") as handle:
            json.dump({"model": None, "language": language, "skipped": "digital_silence", "settings": settings,
                       "mlx_peak_bytes": 0, "text": "", "segments": []}, handle)
        return
    import mlx_whisper
    from scipy.io import wavfile

    repo, revision = ASR_MODELS[model]
    path = snapshot(repo, revision)
    started = time.time()
    texts, segments = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for first, last in spans:
            source = wav
            if spans != whole:
                source = str(Path(tmp) / "chunk.wav")
                wavfile.write(source, rate, samples[first:last])
            result = mlx_whisper.transcribe(source, path_or_hf_repo=path, language=language, task="transcribe",
                                            word_timestamps=True, condition_on_previous_text=False)
            texts.append(result["text"])
            offset = first / rate
            segments.extend({"start": s["start"] + offset, "end": s["end"] + offset, "text": s["text"],
                             "words": [{"word": w["word"], "start": w["start"] + offset, "end": w["end"] + offset}
                                       for w in s.get("words", [])]} for s in result["segments"])
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"model": repo, "model_revision": revision, "language": language, "settings": settings,
                   "spans_samples": spans, "elapsed_seconds": time.time() - started, "mlx_peak_bytes": mlx_peak_bytes(),
                   "text": " ".join(texts), "segments": segments}, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
