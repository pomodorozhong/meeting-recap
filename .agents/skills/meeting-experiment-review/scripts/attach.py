#!/usr/bin/env python3
"""Attach WhisperKit text to diarization labels as a NEW private run, preserving parent outputs."""
import argparse
import json
import re
import shutil
import sys

from common import artifact, dataset, digest, identifier, now, number, private, run, segments, snapshot, write_new

# Same-speaker words further apart than this become separate turns.
MAX_GAP_SECONDS = 1.0


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


def units(asr, method):
    """Yield (start, end, text) for each word or segment, refusing text that has no word timing."""
    for index, segment in enumerate(asr["segments"]):
        if method == "word":
            words = segment.get("words")
            if not words:
                if clean(segment.get("text", "")).strip():
                    raise ValueError(f"transcript segment {index} has text but no word timestamps; "
                                     "attach with --method seg, or rerun ASR with word timestamps")
                continue
        else:
            words = [{**segment, "word": segment["text"]}]
        for word in words:
            number(word["start"], "word start")
            number(word["end"], "word end")
            if word["end"] < word["start"]:
                raise ValueError(f"transcript segment {index} has a word that ends before it starts")
            yield word["start"], word["end"], clean(word["word"])


def turns(asr, segs, method, max_gap=MAX_GAP_SECONDS):
    output, waiting = [], []
    for start, end, text in units(asr, method):
        if end == start:
            # A zero-length word has no time of its own: it joins the turn just before it, else the next word's.
            if output and not waiting and start - output[-1]["end_seconds"] <= max_gap:
                output[-1]["text"] += text
            else:
                waiting.append((start, text))
            continue
        if waiting:
            far = [at for at, _ in waiting if abs(start - at) > max_gap]
            if far:
                raise ValueError(f"a zero-length word at {far[0]} s has no word within {max_gap} s to join")
            text = "".join(t for _, t in waiting) + text
            waiting = []
        if method == "line":
            t = int(end)
            label = next((s["speaker_id"] for s in segs if s["start_seconds"] <= t <= s["end_seconds"]), None)
            label = label or label_at(segs, t, t + 0.01)
        else:
            label = label_at(segs, start, end)
        label = label or "__unassigned__"
        # A longer silence splits one speaker's words into separate turns, so no turn spans it.
        if output and output[-1]["speaker_id"] == label and start - output[-1]["end_seconds"] <= max_gap:
            output[-1]["end_seconds"] = max(output[-1]["end_seconds"], end)
            output[-1]["text"] += text
        else:
            output.append({"speaker_id": label, "start_seconds": start, "end_seconds": end, "text": text})
    if waiting:
        raise ValueError(f"a zero-length word at {waiting[0][0]} s has no word within {max_gap} s to join")
    return segments(output)


def attach(root, asr_id, diarization_id, new_id, method, max_gap=MAX_GAP_SECONDS):
    identifier(new_id)
    number(max_gap, "max_gap")
    asr, dia = run(root, asr_id), run(root, diarization_id)
    if asr["recording_id"] != dia["recording_id"]:
        raise ValueError("attachment inputs must use the same recording and time origin")
    if asr["status"] != "completed" or dia["status"] != "completed":
        raise ValueError("attachment needs completed parent runs")
    output = turns(artifact(root, asr, "transcript"), artifact(root, dia, "segments"), method, max_gap)
    code = snapshot(root)
    directory = private(root, root / "runs" / new_id)
    try:
        # Creating the directory reserves the ID, so a failure below removes only this caller's own run.
        directory.mkdir(parents=True)
    except FileExistsError:
        raise ValueError("derived run ID already exists") from None
    try:
        write_new(directory / "segments.json", output)
        info = {"id": new_id, "recording_id": asr["recording_id"], "model": "speaker-attachment",
                "status": "completed", "created_at": now(), "code": code,
                "config": {"method": method, "max_gap_seconds": max_gap},
                "parents": [asr_id, diarization_id], "artifacts": {
                    "segments": {"path": str((directory / "segments.json").relative_to(root)),
                                 "sha256": digest(directory / "segments.json")}}}
        write_new(directory / "run.json", info)
    except Exception:
        # Leave no half-written run behind, so the same ID can be retried.
        shutil.rmtree(directory, ignore_errors=True)
        raise
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset")
    parser.add_argument("--asr-run", required=True)
    parser.add_argument("--diarization-run", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--method", choices=["line", "seg", "word"], default="word")
    parser.add_argument("--max-gap", type=float, default=MAX_GAP_SECONDS,
                        help="seconds of silence that split one speaker's words into separate turns")
    args = parser.parse_args()
    print(json.dumps(attach(dataset(args.dataset), args.asr_run, args.diarization_run, args.id, args.method,
                            args.max_gap), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        sys.exit(str(error))
