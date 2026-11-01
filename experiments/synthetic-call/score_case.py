"""Score a completed benchmark case against the references for its exact input WAV."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

import numpy as np
from opencc import OpenCC
from scipy.optimize import linear_sum_assignment

from score_speakers import diarization_agreement, load, sha256, transcript_agreement, words


def normalize(text, convert):
    return "".join(c for c in convert(text).casefold() if c.isalnum())


def edit_distance(reference, observed):
    previous = list(range(len(observed) + 1))
    for i, expected in enumerate(reference, start=1):
        current = [i]
        for j, actual in enumerate(observed, start=1):
            current.append(min(previous[j] + 1, current[-1] + 1, previous[j - 1] + (expected != actual)))
        previous = current
    return previous[-1]


def speaker_time(truth, predicted, duration):
    """Exact event intervals, one-to-one maximum coactivity mapping, overlap included, zero collar."""
    events = defaultdict(list)
    events[0.0] = []
    events[duration] = []
    for side, rows in enumerate((truth, predicted)):
        for row in rows:
            start, end = (float(row[k]) for k in ("start_seconds", "end_seconds"))
            if not np.isfinite([start, end]).all() or end < start:
                raise ValueError("invalid segment bounds")
            start, end = max(0.0, start), min(duration, end)
            if start < end:
                label = str(row["speaker_id"])
                events[start].append((side, label, 1))
                events[end].append((side, label, -1))
    active = [Counter(), Counter()]
    totals = Counter()
    common = Counter()
    previous = 0.0
    for timestamp, changes in sorted(events.items()):
        dt = timestamp - previous
        ref, hyp = ([label for label, n in counter.items() if n] for counter in active)
        totals["reference"] += dt * len(ref)
        totals["miss"] += dt * max(0, len(ref) - len(hyp))
        totals["false_alarm"] += dt * max(0, len(hyp) - len(ref))
        totals["comparable"] += dt * min(len(ref), len(hyp))
        for a in ref:
            for b in hyp:
                common[a, b] += dt
        for side, label, delta in changes:
            active[side][label] += delta
        previous = timestamp
    ref_labels, hyp_labels = (sorted(counter) for counter in active)
    weights = np.zeros((len(ref_labels), len(hyp_labels)))
    for i, a in enumerate(ref_labels):
        for j, b in enumerate(hyp_labels):
            weights[i, j] = common[a, b]
    i, j = linear_sum_assignment(weights, maximize=True)
    confusion = max(0.0, totals["comparable"] - float(weights[i, j].sum()))
    errors = totals["miss"] + totals["false_alarm"] + confusion
    return {"labels": len(hyp_labels), "reference_s": totals["reference"], "miss_s": totals["miss"],
            "false_alarm_s": totals["false_alarm"], "confusion_s": confusion,
            "error_rate": errors / totals["reference"] if totals["reference"] else None}


def time_stats(path):
    txt = path.read_text()
    return {"wall_seconds": float(re.search(r"([\d.]+) real", txt).group(1)),
            "peak_footprint_bytes": int(re.search(r"(\d+)\s+peak memory footprint", txt).group(1))}


def score(source, out):
    manifest = load(source / "manifest.json")
    digest = sha256(source / "call.wav")
    pipeline = out / "pipeline"
    if not digest == manifest["call_sha256"] == (out / "input.sha256").read_text().strip() == load(
            pipeline / "run.json")["input_sha256"]:
        raise ValueError("reference and benchmark must describe the same audio")
    convert = OpenCC("t2s").convert
    reference = normalize(load(source / "transcript.json")["text"], convert)
    truth = load(source / "segments.json")
    seconds = manifest["duration_seconds"]
    result = {"audio_sha256": digest, "duration_seconds": seconds, "reference_characters": len(reference),
              "reference_turns": len(truth), "asr": {}, "diarization": {}, "word_label_agreement": {}}
    asrs = {"whisper": load(pipeline / "asr.json"), "breeze": load(out / "breeze.json")}
    if (out / "extension/turbo.json").is_file():
        asrs["turbo-q4"] = load(out / "extension/turbo.json")
    stages = load(pipeline / "stages.json")
    long_gaps = [(a["end_seconds"], b["start_seconds"]) for a, b in zip(truth, truth[1:])
                 if b["start_seconds"] - a["end_seconds"] >= 10]
    for name, data in asrs.items():
        observed = normalize(data["text"], convert)
        errors = edit_distance(reference, observed)
        if name == "whisper":
            timing = stages["asr"]
        else:
            timing = time_stats(out / ("breeze.time" if name == "breeze" else "extension/turbo.time"))
        result["asr"][name] = {"errors": errors, "observed_characters": len(observed),
                               "cer": errors / len(reference) if reference else None,
                               "wall_seconds": timing["wall_seconds"],
                               "decode_seconds": data["elapsed_seconds"] if name == "whisper" else data["elapsed"],
                               "peak_footprint_bytes": timing["peak_footprint_bytes"]}
        repeats = out / "extension/repeats"
        if repeats.is_dir():
            rows = []
            for n in (2, 3):
                file = repeats / f"{name}-{n}.json"
                text = normalize(load(file)["text"], convert)
                rows.append({"same_normalized_text_as_first": text == observed, "errors": edit_distance(reference, text),
                             **time_stats(file.with_suffix(".time"))})
            result["asr"][name]["repeat_runs"] = rows
        if long_gaps:
            result["asr"][name]["word_midpoints_in_long_gaps"] = sum(
                any(left < (start + end) / 2 < right for left, right in long_gaps)
                for start, end, _ in words(data))
    diarizers = {"sortformer": load(pipeline / "diarization.json"), "who": load(out / "who.json")["segments"]}
    if out.name in ("handoff", "logistics"):
        for name in ("community", "community-count", "lseend-dihard3", "lseend-ami", "lseend-callhome", "lseend-dihard2"):
            diarizers[name] = load(out / f"{name}.json")
    for name, segments in diarizers.items():
        metrics = speaker_time(truth, segments, seconds)
        timing = stages["diarize"] if name == "sortformer" else time_stats(out / f"{name}.time")
        metrics.update(wall_seconds=timing["wall_seconds"], peak_footprint_bytes=timing["peak_footprint_bytes"])
        result["diarization"][name] = metrics
        # On digital silence an invented word agrees with both empty speaker maps.
        # Only the absolute false-character and false-alarm counts have meaning there.
        if truth and name in ("sortformer", "who"):
            for asr, data in asrs.items():
                mapping, agreement = diarization_agreement(data, segments, truth)
                if name == "sortformer" and asr == "whisper":
                    aligned = transcript_agreement(load(pipeline / "turns.json"),
                                                   load(source / "transcript.json")["segments"], mapping, convert)
                    result["attached_transcript"] = {k: aligned[k] for k in ("aligned", "agree", "script_characters")}
                result["word_label_agreement"][f"{asr}-{name}"] = {
                    k: agreement[k] for k in ("characters", "agree")}
    if "summary" in stages:
        result["recap"] = {k: stages["summary"][k] for k in ("wall_seconds", "peak_footprint_bytes")}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("result_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(score(args.source, args.result_dir), indent=2))
