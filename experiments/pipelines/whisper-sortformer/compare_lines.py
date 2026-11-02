"""Explore line boundaries from cached ASR and Who predictions; never replace a previous recap."""
import argparse
from pathlib import Path

import pipeline
import recap


def render(asr_path, diarization_path, audio, output, keep_segments, speakers=None):
    if any((p / ".git").exists() for p in (output, *output.parents)):
        raise ValueError("output must be a new folder outside Git")
    asr = recap.read_json(asr_path)
    raw = recap.read_json(diarization_path)
    segments = pipeline.who_segments(raw) if isinstance(raw, dict) else raw
    turns = pipeline.attach(asr, segments, keep_segments=keep_segments)
    mapping = recap.read_json(speakers) if speakers else pipeline.default_speakers(turns)
    pipeline.check_speakers(mapping, turns)
    output.mkdir()
    recap.write_atomic(output / "turns.json", turns)
    recap.write_atomic(output / "speakers.json", mapping)
    (output / "audio.wav").symlink_to(audio.resolve())
    recap.write_atomic(output / "comparison.json", {"asr_sha256": recap.sha256(asr_path),
                      "diarization_sha256": recap.sha256(diarization_path), "audio_sha256": recap.sha256(audio),
                      "keep_segments": keep_segments, "code_commit": recap.git_commit()})
    recap.transcript(output)
    rec = recap.Run(output)
    rec.stage("summary", lambda: recap.summary(output), ["summary.json", "summary.md"])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("asr", "segments", "audio", "out"):
        p.add_argument(key, type=Path)
    p.add_argument("--keep-segments", action="store_true")
    p.add_argument("--speakers", type=Path)
    args = p.parse_args()
    render(args.asr, args.segments, args.audio, args.out.resolve(), args.keep_segments, args.speakers)
