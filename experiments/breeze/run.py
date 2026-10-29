"""Transcribe a 16 kHz WAV with Breeze-ASR-25 and write WhisperKit-shaped JSON."""
import json, sys, time
import numpy as np, soundfile as sf, torch
from transformers import pipeline

wav, out = sys.argv[1], sys.argv[2]
device = "mps" if torch.backends.mps.is_available() else "cpu"
asr = pipeline("automatic-speech-recognition", model="MediaTek-Research/Breeze-ASR-25",
               revision="cffe7ccb404d025296a00758d0a33468bec3a9d0",
               torch_dtype=torch.float16 if device == "mps" else torch.float32, device=device)
audio, sr = sf.read(wav, dtype="float32")
t = time.time()
res = asr({"raw": audio, "sampling_rate": sr}, chunk_length_s=30, batch_size=1, return_timestamps="word",
          generate_kwargs={"language": "zh", "task": "transcribe"})
elapsed = time.time() - t
words = [{"word": c["text"], "start": c["timestamp"][0], "end": c["timestamp"][1] or c["timestamp"][0]} for c in res["chunks"]]
# group words into pseudo-segments of ~10 s for line-level metrics
segs, cur = [], []
for w in words:
    if cur and w["start"] - cur[0]["start"] > 10:
        segs.append(cur); cur = []
    cur.append(w)
if cur: segs.append(cur)
json.dump({"text": res["text"], "elapsed": elapsed, "segments": [
    {"start": s[0]["start"], "end": s[-1]["end"], "text": "".join(w["word"] for w in s), "words": s} for s in segs]},
    open(out, "w"), ensure_ascii=False, indent=1)
print(device, f"{elapsed:.1f}s", res["text"][:200])
