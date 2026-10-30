#!/usr/bin/env python3
"""Attach WhisperKit text to diarization labels as a NEW private run, preserving parent outputs."""
import argparse
import json
import re
import sys

from common import artifact, dataset, digest, identifier, now, run, snapshot, write_new


def clean(text):
    return re.sub(r"<\|[^|]*\|>", "", text)


def label_at(segs, start, end):
    best, overlap = None, 0.0
    for segment in segs:
        amount = min(end, segment["end_seconds"]) - max(start, segment["start_seconds"])
        if amount > overlap:
            best, overlap = segment["speaker_id"], amount
    if best is None and segs:
        mid = (start + end) / 2
        distance, best = min((min(abs(mid - s["start_seconds"]), abs(mid - s["end_seconds"])), s["speaker_id"]) for s in segs)
        if distance > 1:
            best = None
    return best


def turns(asr, segs, method):
    output = []
    for segment in asr["segments"]:
        if method == "word":
            if "words" not in segment:
                raise ValueError("word attachment requires word timestamps; choose seg explicitly instead")
            units = segment["words"]
        else:
            units = [{**segment, "word": segment["text"]}]
        for unit in units:
            start, end = unit["start"], unit["end"]
            if method == "line":
                t = int(end)
                label = next((s["speaker_id"] for s in segs if s["start_seconds"] <= t <= s["end_seconds"]), None)
                label = label or label_at(segs, t, t + 0.01)
            else:
                label = label_at(segs, start, end)
            label = label or "__unassigned__"
            text = clean(unit["word"])
            if output and output[-1]["speaker_id"] == label:
                output[-1]["end_seconds"] = end
                output[-1]["text"] += text
            else:
                output.append({"speaker_id": label, "start_seconds": start, "end_seconds": end, "text": text})
    return output


def attach(root, asr_id, diarization_id, new_id, method):
    identifier(new_id)
    asr, dia = run(root, asr_id), run(root, diarization_id)
    if asr["recording_id"] != dia["recording_id"]:
        raise ValueError("attachment inputs must use the same recording and time origin")
    if asr["status"] != "completed" or dia["status"] != "completed":
        raise ValueError("attachment needs completed parent runs")
    output = turns(artifact(root, asr, "transcript"), artifact(root, dia, "segments"), method)
    directory = root / "runs" / new_id
    if directory.exists():
        raise ValueError("derived run ID already exists")
    write_new(directory / "segments.json", output)
    info = {"id": new_id, "recording_id": asr["recording_id"], "model": "speaker-attachment",
            "status": "completed", "created_at": now(), "code": snapshot(root), "config": {"method": method},
            "parents": [asr_id, diarization_id], "artifacts": {
                "segments": {"path": str((directory / "segments.json").relative_to(root)),
                             "sha256": digest(directory / "segments.json")}}}
    write_new(directory / "run.json", info)
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset")
    parser.add_argument("--asr-run", required=True)
    parser.add_argument("--diarization-run", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--method", choices=["line", "seg", "word"], default="word")
    args = parser.parse_args()
    print(json.dumps(attach(dataset(args.dataset), args.asr_run, args.diarization_run, args.id, args.method), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        sys.exit(str(error))
