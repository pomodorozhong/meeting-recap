#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["opencc-python-reimplemented"]
# ///
"""Choose review clips from registered runs and write a session plan (seeded and repeatable).

Speaker-order clips: windows starting `lead_seconds` before a predicted turn change, one per
equal time bin after `skip_before`, plus one on the rarest diarization label (a voice split
across two labels shows up there). Transcript clips: windows where two transcript runs differ
most after OpenCC s2tw normalization, plus the median window for a fair comparison.
"""
import argparse
import difflib
import json
import random
import re
import sys
from collections import Counter

from common import dataset, identifier, inside, read_json, recording, run, write_new

DEFAULTS = {"window_seconds": 15, "lead_seconds": 4, "min_overlap": 0.3, "min_turns": 2, "max_turns": 5,
            "min_gap_seconds": 20, "transcript_gap_seconds": 60, "min_characters": 30,
            "normalize": "both"}


def artifact(root, run_id, name):
    info = run(root, run_id)
    if info["status"] != "completed":
        raise ValueError(f"run {run_id} is {info['status']}")
    return info, read_json(inside(root, info["artifacts"][name]["path"]))


def turns(segs, start, end, min_overlap):
    seq = []
    for s in sorted(segs, key=lambda s: s["start_seconds"]):
        if min(end, s["end_seconds"]) - max(start, s["start_seconds"]) >= min_overlap and (not seq or seq[-1] != s["speaker_id"]):
            seq.append(s["speaker_id"])
    return seq


def words(asr, start, end, convert):
    text = "".join(w["word"] for s in asr["segments"] for w in s.get("words", []) if w["start"] >= start and w["end"] <= end)
    return convert(re.sub(r"\s+", "", text))


def select(root, config):
    o = {**DEFAULTS, **config}
    rng = random.Random(o["seed"])
    window = o["window_seconds"]
    speaker_items, transcript_items, shortfall = [], [], []
    convert = None
    for rec in o["recordings"]:
        rec_id = rec["recording_id"]
        duration = recording(root, rec_id)["duration_seconds"]
        skip = rec.get("skip_before", 0)
        if rec.get("speaker_clips"):
            info, segs = artifact(root, rec["diarization_run"], "segments")
            if info["recording_id"] != rec_id:
                raise ValueError("diarization run names a different recording")
            cands = []
            for s in segs:
                a = s["start_seconds"] - o["lead_seconds"]
                if a < skip or a + window > duration:
                    continue
                seq = turns(segs, a, a + window, o["min_overlap"])
                if o["min_turns"] <= len(seq) <= o["max_turns"]:
                    cands.append((a, seq))
            totals = Counter()
            for s in segs:
                totals[s["speaker_id"]] += s["end_seconds"] - s["start_seconds"]
            rarest = min(totals, key=totals.get) if len(totals) > 1 else None
            rare = [c for c in cands if rarest in c[1]]
            pick = [rng.choice(rare)] if rare else []
            bins = rec["speaker_clips"] - len(pick)
            width = (duration - skip) / bins if bins else 0
            for i in range(bins):
                start, end = skip + i * width, skip + (i + 1) * width
                inbin = [c for c in cands if start <= c[0] < end and len(set(c[1])) >= 2]
                spaced = [c for c in inbin if all(abs(c[0] - p[0]) > o["min_gap_seconds"] for p in pick)]
                # When every candidate is near an earlier pick, take one that at least does not overlap it.
                apart = [c for c in inbin if all(abs(c[0] - p[0]) >= window for p in pick)]
                if spaced or apart:
                    pick.append(rng.choice(spaced or apart))
                else:
                    shortfall.append({"recording_id": rec_id, "task": "speaker_order",
                                      "bin_seconds": [round(start, 2), round(end, 2)],
                                      "why": "no turn-change window in this bin that does not overlap another clip"})
            for a, seq in sorted(pick):
                reason = (f"Rarest diarization label ({totals[rarest]:.0f} s in all; possible split voice)" if rarest in seq
                          else f"Turn change, time bin sample ({len(seq)} predicted turns)")
                speaker_items.append({"task": "speaker_order", "recording_id": rec_id, "start_seconds": round(a, 2),
                                      "end_seconds": round(a + window, 2), "padding_seconds": 1, "reason": reason,
                                      "run_ids": rec.get("speaker_show_runs", [rec["diarization_run"]])})
        if rec.get("transcript_clips"):
            if convert is None:
                try:
                    from opencc import OpenCC
                except ImportError:
                    raise ValueError("transcript selection needs opencc; run with `uv run pick_clips.py ...`")
                convert = OpenCC("s2tw").convert
            first, second = rec["transcript_runs"]
            texts = []
            for run_id in (first, second):
                info, asr = artifact(root, run_id, "transcript")
                if info["recording_id"] != rec_id:
                    raise ValueError("transcript run names a different recording")
                texts.append(asr)
            if o["normalize"] not in {"both", "first"}:
                raise ValueError("normalize must be both or first")
            # "first" converts only the first run, as the 2026-10-29 session did.
            keep = (lambda text: text) if o["normalize"] == "first" else convert
            ranked = []
            for a in range(int(skip), int(duration) - window, window):
                x, y = words(texts[0], a, a + window, convert), words(texts[1], a, a + window, keep)
                if len(x) + len(y) > o["min_characters"]:
                    ranked.append((1 - difflib.SequenceMatcher(None, x, y).ratio(), a))
            ranked.sort(reverse=True)
            if not ranked:
                raise ValueError(f"no transcript windows with speech in {rec_id}")
            chosen = []
            for d, a in ranked:
                if len(chosen) < rec["transcript_clips"] and all(abs(a - b) > o["transcript_gap_seconds"] for _, b in chosen):
                    chosen.append((d, a))
            if len(chosen) < rec["transcript_clips"]:
                shortfall.append({"recording_id": rec_id, "task": "transcript", "missing": rec["transcript_clips"] - len(chosen),
                                  "why": "not enough windows with speech spaced transcript_gap_seconds apart"})
            entries = [(a, f"Transcript runs disagree most here ({d:.0%} different after s2tw)") for d, a in chosen]
            median = ranked[len(ranked) // 2]
            entries.append((median[1], f"Typical disagreement ({median[0]:.0%}) for a fair comparison"))
            for a, reason in entries:
                transcript_items.append({"task": "transcript", "recording_id": rec_id, "start_seconds": float(a),
                                         "end_seconds": float(a + window), "padding_seconds": 0, "reason": reason,
                                         "run_ids": [first, second]})
    items = [{"id": f"c{n:02d}", **item} for n, item in enumerate(speaker_items + transcript_items, 1)]
    method = {k: o[k] for k in DEFAULTS} | {"recordings": o["recordings"]}
    return {"id": identifier(o["id"]), "question": o["question"],
            "selector": {"name": "pick_clips.py", "version": "1", "seed": o["seed"], "method": method,
                         "shortfall": shortfall}, "items": items}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset")
    parser.add_argument("--config", required=True, help="selection JSON; see SKILL.md step 3")
    parser.add_argument("--out", required=True, help="new plan JSON path, outside the repository")
    args = parser.parse_args()
    plan = select(dataset(args.dataset), read_json(args.config))
    write_new(args.out, plan)
    print(json.dumps({"plan": args.out, "items": len(plan["items"]), "shortfall": plan["selector"]["shortfall"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        sys.exit(str(error))
