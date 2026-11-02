"""Run pinned EmotiVoice presets in their own locked CPU environment."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
PROJECT = HERE / "emotivoice"
VOICE_IDS = frozenset({"emotivoice-1093", "emotivoice-1012", "emotivoice-1066"})


def provenance(voice):
    """Read voice and runtime pins without importing the synthesis libraries."""
    if voice not in VOICE_IDS:
        raise ValueError(f"unsupported EmotiVoice profile: {voice}")
    pin = json.loads((PROJECT / "pins.json").read_text())
    pin["voice"] = voice
    pin["speaker_id"] = pin["voices"][voice]["speaker_id"]
    pin["models"] = {asset["repository"]: asset["revision"] for asset in pin["artifacts"].values()}
    pin["uv_lock_sha256"] = hashlib.sha256((PROJECT / "uv.lock").read_bytes()).hexdigest()
    return pin


@contextmanager
def render_turns(turns, speakers, seed):
    """Yield native FLOAT WAVs for every EmotiVoice turn, then clean them up."""
    requests = [{"index": index, "voice": speakers[turn["speaker"]]["voice"], "text": turn["text"]}
                for index, turn in enumerate(turns)
                if speakers[turn["speaker"]]["voice"] in VOICE_IDS]
    if not requests:
        yield {}
        return
    with tempfile.TemporaryDirectory(prefix="synthetic-emotivoice-") as temporary:
        root = Path(temporary)
        request = root / "request.json"
        request.write_text(json.dumps({"seed": seed, "turns": requests}, ensure_ascii=False))
        output = root / "audio"
        subprocess.run(["uv", "run", "--frozen", "--project", str(PROJECT), "python",
                        str(PROJECT / "render.py"), str(request), str(output)], check=True)
        clips = {item["index"]: output / f"{item['index']:03d}.wav" for item in requests}
        if not all(path.is_file() for path in clips.values()):
            raise ValueError("EmotiVoice did not render every requested turn")
        yield clips
