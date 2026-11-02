"""Score the registered 17-file matrix; emits only hashes, counts, timings and fitted label metrics."""
import argparse
import contextlib
from collections import Counter, defaultdict
from importlib.metadata import version
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment
import soundfile as sf

from collection import CONTROLS, HERE, SCRIPTS, build, digest, load
from expanded_followup import MODELS, PIPE, chunks
from score_transcripts import edit_distance, normalizers
from score_speakers import score as score_speakers, words


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


def attribution(src, case, model, diarizer, segments):
    # Call the actual pipeline attachment in its own project. The reference is only used for scoring.
    asr = load(case / f"{model}.json")
    command = "import json,sys,pipeline; print(json.dumps(pipeline.attach(*json.load(sys.stdin))))"
    turns = json.loads(subprocess.check_output([PIPE / ".venv/bin/python", "-c", command], cwd=PIPE,
                                               input=json.dumps([asr, segments]), text=True))
    scored = score_speakers(asr, segments, load(src / "manifest.json")["call_sha256"], turns, src)
    return {"asr":model, "diarizer":diarizer, "word_time":{k:scored["diarization"][k] for k in ("characters","agree")},
            "delivered":{k:scored["transcript"][k] for k in ("script_characters","aligned","agree")}}


def pipeline_timing(case, arm):
    stats = time_stats(case / (arm + ".time"))
    # /usr/bin/time on the driver misses the model subprocesses it launches.
    stats["driver_peak_footprint_bytes"] = stats.pop("peak_footprint_bytes")
    stages = load(case / arm / "stages.json")
    stats["peak_stage_footprint_bytes"] = max(v.get("peak_footprint_bytes", 0) for v in stages.values())
    return stats


def aggregate(report):
    groups = {}
    for model in MODELS:
        for mode in ("whole", "split"):
            values = groups.setdefault(model, {}).setdefault(mode, {})
            for lang in ("en", "zh"):
                cases = [v for k, v in report.items() if k in SCRIPTS and v["language"] == lang]
                errors = sum(c["asr"][model][mode + "_errors"] for c in cases)
                total = sum(c["reference_units"] for c in cases)
                values[lang] = {"metric": "WER" if lang == "en" else "CER", "errors": errors,
                                "reference_units": total, "rate": errors / total, "calls": len(cases)}
    return groups


def score(fixtures, results):
    with contextlib.redirect_stdout(sys.stderr):
        build(fixtures, check_only=True)
    normalize = normalizers()
    report = {}
    for name in (*SCRIPTS, *CONTROLS):
        src, case = fixtures / name, results / name
        meta, truth = load(src / "manifest.json"), load(src / "segments.json")
        lang = meta.get("language", "zh")
        pcm, rate = sf.read(src / "call.wav", dtype="int16")
        wave, rate2 = sf.read(case / "audio.wav", dtype="float32")
        if (meta["call_sha256"] != (case / "input.sha256").read_text().strip() or rate != rate2
                or not np.array_equal(pcm.astype("float32") / 32768, wave)):
            raise ValueError(f"conversion or input digest differs: {name}")
        reference = normalize[lang](load(src / "transcript.json")["text"])
        split = case / "split"
        spans = chunks(pcm)
        if load(split / "spans.json") != [list(s) for s in spans]:
            raise ValueError(f"incorrect pause intervals: {name}")
        passthrough = spans == [(0, len(pcm))]
        expected_speakers = len({s["speaker_id"] for s in truth})
        row = {"audio_sha256": meta["call_sha256"], "language": lang, "seconds": meta["duration_seconds"],
               "reference_units": len(reference), "reference_speakers": expected_speakers, "asr": {},
               "split_spans_samples": spans, "diarizers": {}}
        for model in [*MODELS, *(["shipping-zh"] if lang == "en" else [])]:
            path = case / (model + ".json")
            d = load(path)
            if ((d["model"], d["model_revision"]) != MODELS.get(model, MODELS["whisper"])
                    or d["language"] != ("zh" if model == "shipping-zh" else lang)):
                raise ValueError(f"wrong decode provenance: {name}/{model}")
            observed = normalize[lang](d["text"])
            result = {"sha256": digest(path), "whole_errors": edit_distance(reference, observed),
                      "observed_units": len(observed), **time_stats(case / f"{model}.time")}
            gaps = [(a["end_seconds"], b["start_seconds"]) for a, b in zip(truth, truth[1:])
                    if b["start_seconds"] - a["end_seconds"] >= 5]
            def gap_words(asr, arm):
                try:
                    return sum(any(a < (s+e)/2 < b for a, b in gaps) for s, e, _ in words(asr))
                except ValueError as error:
                    if "text but no word timestamps" not in str(error):
                        raise
                    result[arm + "_gap_diagnostic_unavailable"] = str(error)
                    return None
            if model in MODELS:
                sliced = d if passthrough else load(split / f"{model}.json")
                result["split_errors"] = edit_distance(reference, normalize[lang](sliced["text"]))
                if gaps:
                    result.update(whole_words_in_gap=gap_words(d, "whole"), split_words_in_gap=gap_words(sliced, "split"))
                if not passthrough:
                    timings = [time_stats(split / f"{model}-{i}.time") for i in range(len(spans))]
                    result.update(split_sha256=digest(split / f"{model}.json"),
                                  split_decode_wall_seconds=sum(t["wall_seconds"] for t in timings),
                                  split_peak_footprint_bytes=max((t["peak_footprint_bytes"] for t in timings), default=0))
            if name in ("silence", "handoff"):
                repeat = case / f"{model}-repeat.json"
                result["repeat"] = {**time_stats(repeat.with_suffix(".time")), "sha256": digest(repeat),
                                    "same_normalized_text": observed == normalize[lang](load(repeat)["text"])}
            row["asr"][model] = result
        for model in ["who", "sortformer"] + (["community", "community-count", "lseend-dihard3", "lseend-ami",
                                               "lseend-callhome", "lseend-dihard2"]
                                              if name in ("onboarding","english-committee","english-tabletop") else []):
            path = case / (model + ".json")
            data = load(path)
            segs = data["segments"] if model == "who" else data
            if truth and model in ("who", "sortformer"):
                for recognizer in ("turbo", "whisper"):
                    row.setdefault("attribution", {})[f"{recognizer}-{model}"] = attribution(
                        src, case, recognizer, model, segs)
            row["diarizers"][model] = {**speaker_time(truth, segs, meta["duration_seconds"]),
                                      **time_stats(case / f"{model}.time"), "sha256": digest(path)}
        if name != "silence":
            ev = load(case / "turn-order.json")
            # Do not publish a local path or transcript embedded in a validation error.
            row["turn_order"] = {"excluded": ev["excluded"], "refused_runs": sorted(ev["errors"]),
                                 "results": ev["results"], "code": ev["code"]}
        if name in ("onboarding", "english-audit"):
            row["recap"] = {}
            for arm in ("pipeline", "exact", "fast"):
                summary = case / arm / "summary.json"
                row["recap"][arm] = {**pipeline_timing(case, arm), "summary_sha256": digest(summary),
                                      "checks": load(summary)["checks"]}
            row["recap"]["pipeline"]["stages"] = {
                k: {m:v[m] for m in ("seconds","peak_footprint_bytes") if m in v}
                for k,v in load(case / "pipeline/stages.json").items()}
        if name == "silence":
            silent = case / "pipeline"
            if (load(silent / "asr.json")["skipped"] != "digital_silence"
                    or load(silent / "turns.json") or any(load(silent / "summary.json")["notes"].values())):
                raise ValueError("silence control did not produce empty notes")
            row["silent_pipeline"] = {**pipeline_timing(case, "pipeline"), "turns": 0,
                                      "notes": 0, "summary_sha256": digest(silent / "summary.json")}
        report[name] = row
    return {"normalizers": {n: version(n) for n in ("transformers", "opencc-python-reimplemented")},
            "models": MODELS, "weights": load(results / "onboarding/weights.json"),
            "groups": aggregate(report), "cases": report}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("fixtures", type=Path)
    p.add_argument("results", type=Path)
    args = p.parse_args()
    print(json.dumps(score(args.fixtures.resolve(), args.results.resolve()), indent=2, allow_nan=False))
