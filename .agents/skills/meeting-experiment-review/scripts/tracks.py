#!/usr/bin/env python3
"""Find who speaks when from separate per-speaker tracks, such as a two-person call's mic and system audio.

Each track is a 16-bit PCM WAV (convert with `ffmpeg -i mic.m4a -ac 1 -ar 16000 mic.wav`). A frame is
active when its level is `margin_db` above the track's noise floor (its 10th-percentile frame level) and
above `floor_db`; active runs closer than `min_gap_seconds` merge, and runs shorter than
`min_speech_seconds` are dropped. This is a level gate, not a speech detector: it is only a reference
when each track holds one speaker and the other side does not leak into it (headphones).
"""
from __future__ import annotations

import argparse
import json
import math
import operator
import sys
import wave
from array import array

from common import number, outside_git

SETTINGS = {"frame_seconds": 0.03, "margin_db": 15.0, "floor_db": -50.0,
            "min_gap_seconds": 0.3, "min_speech_seconds": 0.2}


def levels(path, frame_seconds):
    """Return (frame levels in dBFS, duration in seconds, sample rate) of a 16-bit PCM WAV, channels averaged."""
    try:
        with wave.open(str(path), "rb") as handle:
            if handle.getsampwidth() != 2 or handle.getcomptype() != "NONE":
                raise ValueError(f"{path}: tracks must be 16-bit PCM WAV")
            channels, rate, count = handle.getnchannels(), handle.getframerate(), handle.getnframes()
            samples = array("h", handle.readframes(count))
    except (wave.Error, EOFError) as error:
        raise ValueError(f"{path}: not a readable WAV ({error})") from None
    if sys.byteorder == "big":
        samples.byteswap()
    size = max(1, round(frame_seconds * rate)) * channels
    out = []
    for i in range(0, len(samples), size):
        frame = samples[i:i + size]
        power = sum(map(operator.mul, frame, frame)) / len(frame)
        out.append(10 * math.log10(power / 32768 ** 2) if power else -math.inf)
    return out, count / rate, rate


def activity(path, settings=SETTINGS):
    """Return the active (start, end) spans of one track in seconds, and the track's duration."""
    for key in SETTINGS:
        number(settings[key], key, minimum=-200 if key == "floor_db" else 0)
    step = settings["frame_seconds"]
    if step <= 0:
        raise ValueError("frame_seconds must be positive")
    dbs, duration, rate = levels(path, step)
    # Frames are whole samples, so a frame lasts slightly more or less than frame_seconds; time counts real frames.
    step = max(1, round(step * rate)) / rate
    quiet = sorted(dbs)[len(dbs) // 10] if dbs else -math.inf
    threshold = max(quiet + settings["margin_db"], settings["floor_db"])
    spans = []
    for i, db in enumerate(dbs):
        if db < threshold:
            continue
        start, end = i * step, min((i + 1) * step, duration)
        if spans and start - spans[-1][1] < settings["min_gap_seconds"]:
            spans[-1][1] = end
        else:
            spans.append([start, end])
    # Keep sample-derived bounds: rounding up can put the final span past the WAV's duration.
    return [(a, b) for a, b in spans if b - a >= settings["min_speech_seconds"]], duration


def track_segments(tracks, settings=SETTINGS, tolerance_seconds=1.0):
    """Turn {speaker_id: wav path} into a segments artifact, checking that the tracks share one timeline."""
    if len(tracks) != 2:
        raise ValueError("a track reference needs exactly two tracks, one speaker each")
    rows, durations = [], []
    for speaker, path in tracks.items():
        if not isinstance(speaker, str) or not speaker:
            raise ValueError("track speaker IDs must be nonempty strings")
        spans, duration = activity(path, settings)
        durations.append(duration)
        rows += [{"speaker_id": speaker, "start_seconds": a, "end_seconds": b} for a, b in spans]
    if max(durations) - min(durations) > tolerance_seconds:
        raise ValueError("tracks differ in length; they must share one timeline")
    return sorted(rows, key=lambda s: (s["start_seconds"], s["speaker_id"])), max(durations)


def parse_tracks(values):
    tracks = {}
    for value in values:
        speaker, sep, path = value.partition("=")
        if not sep or not speaker or not path or speaker in tracks:
            raise ValueError("pass each track once as SPEAKER=path.wav")
        tracks[speaker] = path
    return tracks


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--track", action="append", required=True, help="SPEAKER=path.wav, once per track")
    parser.add_argument("--out", required=True, help="segments JSON to write (private; keep it in the dataset or scratch)")
    args = parser.parse_args()
    out = outside_git(args.out)
    rows, duration = track_segments(parse_tracks(args.track))
    with open(out, "x", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)
        handle.write("\n")
    speech = {}
    for row in rows:
        speech[row["speaker_id"]] = speech.get(row["speaker_id"], 0) + row["end_seconds"] - row["start_seconds"]
    print(json.dumps({"duration_seconds": duration, "segments": len(rows),
                      "speech_seconds": {k: round(v, 1) for k, v in speech.items()}}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        sys.exit(str(error))
