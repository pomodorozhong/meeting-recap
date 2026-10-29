"""Run pyannote speaker-diarization-community-1 on a WAV and write segments JSON."""
import json, sys, time
import torch
from pyannote.audio import Pipeline

wav, out = sys.argv[1], sys.argv[2]
kwargs = {}
if len(sys.argv) > 3:
    kwargs["num_speakers"] = int(sys.argv[3])
pipe = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1")
device = "mps" if torch.backends.mps.is_available() else "cpu"
pipe.to(torch.device(device))
t = time.time()
result = pipe(wav, **kwargs)
elapsed = time.time() - t
ann = getattr(result, "exclusive_speaker_diarization", None) or getattr(result, "speaker_diarization", result)
segs = [{"speaker_id": spk, "start_seconds": turn.start, "end_seconds": turn.end}
        for turn, _, spk in ann.itertracks(yield_label=True)]
json.dump(segs, open(out, "w"), indent=1)
tot = {}
for s in segs: tot[s["speaker_id"]] = tot.get(s["speaker_id"], 0) + s["end_seconds"] - s["start_seconds"]
print(device, f"{elapsed:.1f}s", {k: round(v) for k, v in sorted(tot.items())})
