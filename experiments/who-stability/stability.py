#!/usr/bin/env python3
"""Simulate live speaker labels from Who reruns on growing prefixes, and measure how stable they are.

usage: stability.py FIXTURES PREFIXES.json > stability.json

PREFIXES.json is who-prefixes' output: for each call, Who's labels on prefixes every STEP seconds and on
the whole call. FIXTURES is the synthetic collection; each call's segments.json gives the known turns.

For every update interval (a multiple of STEP) and lock delay, one live display is simulated per call, on
a 10 ms grid with one row per shown ID, so overlapping speech keeps both labels:

1. At each update at time t, Who's run on [0, t] is mapped to the shown IDs by how much each run label
   overlaps each shown ID on the audio the previous update covered. The mapping is one-to-one and
   maximizes total overlap (Hungarian); a pair counts only with at least MIN_MATCH seconds in common.
2. A run label left unmatched gets a new shown ID. A shown ID left unmatched whose covered time lies
   mostly (at least half) inside one run label is merged into that label's ID, from then on.
3. Frames older than t - LOCK are locked and never rewritten; newer frames take the mapped run's labels.

A known turn's label is the shown ID covering most of its time. Measured per update, before writing:
- locked changes: a locked turn (ended by t - LOCK) whose label under the mapped run differs from its
  locked label (after merges), meaning the display would have changed it had it not been locked;
- provisional changes: a turn already shown, not yet locked, whose label the update changes;
- settle time: after the last update, how long after a turn ended its label last changed;
- first label right: whether the first label shown for a turn is the one the turn ends with, after mapping
  shown IDs one-to-one to known speakers on the final display;
- speaker-time error of the final display (locked turns as locked) next to Who's own run on the whole call,
  with collection_scores.speaker_time (one-to-one mapping, overlap included, zero collar).
"""
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "synthetic-call"))
from collection_scores import speaker_time  # noqa: E402

RATE = 100  # frames per second
MIN_MATCH = 0.5  # seconds in common for a run label to keep a shown ID
INTERVALS = (15, 30, 60)
LOCKS = (30, 60, 120, None)  # None: never lock
SCRIPTED = ("script", "handoff", "logistics", "stocktake", "scheduling", "design", "onboarding", "localization",
            "english-audit", "english-handoff", "english-design", "english-tabletop", "english-committee",
            "english-training")
CONTROLS = ("handoff-channel", "logistics-overlap")


def frames(seconds):
    return int(round(seconds * RATE))


def matrix(segments, labels, n):
    rows = np.zeros((len(labels), n), dtype=bool)
    index = {label: i for i, label in enumerate(labels)}
    for s in segments:
        rows[index[s["speaker_id"]], frames(s["start_seconds"]):frames(s["end_seconds"])] = True
    return rows


def to_segments(shown, n):
    out = []
    for sid, row in enumerate(shown[:, :n]):
        edges = np.flatnonzero(np.diff(np.concatenate(([0], row.astype(np.int8), [0]))))
        out += [{"speaker_id": f"S{sid}", "start_seconds": a / RATE, "end_seconds": b / RATE}
                for a, b in zip(edges[::2], edges[1::2])]
    return out


def turn_label(rows, a, b):
    if rows.shape[0] == 0 or b <= a:
        return None
    counts = rows[:, a:b].sum(axis=1)
    return int(counts.argmax()) if counts.max() > 0 else None


def simulate(runs, turns, duration, interval, lock):
    n_total = frames(duration) + 1
    updates = [r for r in runs if abs(r["prefix_seconds"] / interval - round(r["prefix_seconds"] / interval)) < 1e-6
               or r is runs[-1]]
    shown = np.zeros((0, n_total), dtype=bool)
    turn_frames = [(frames(t["start_seconds"]), frames(t["end_seconds"])) for t in turns]
    history = [[] for _ in turns]  # (update time, label) whenever a turn's shown label changes
    counts = {"locked_checks": 0, "locked_changes": 0, "provisional_checks": 0, "provisional_changes": 0,
              "merges": 0, "new_ids_after_first": 0}
    locked_turns_changed = set()
    n_prev = 0
    for k, run in enumerate(updates):
        t = run["prefix_seconds"]
        n = min(n_total, frames(t))
        labels = sorted({s["speaker_id"] for s in run["segments"]})
        rows = matrix(run["segments"], labels, n_total)
        rows[:, n:] = False
        ids = [-1] * len(labels)
        if shown.shape[0] and labels:
            overlap = (rows[:, None, :n_prev] & shown[None, :, :n_prev]).sum(axis=2) / RATE
            ri, si = linear_sum_assignment(overlap, maximize=True)
            for r, s in zip(ri, si):
                if overlap[r, s] >= MIN_MATCH:
                    ids[r] = int(s)
            matched = set(ids)
            for s in range(shown.shape[0]):
                covered = shown[s, :n_prev].sum() / RATE
                if s in matched or covered == 0:
                    continue
                r = int(overlap[:, s].argmax())
                if ids[r] >= 0 and overlap[r, s] >= 0.5 * covered:  # merged into run label r's shown ID
                    shown[ids[r]] |= shown[s]
                    shown[s] = False
                    counts["merges"] += 1
        for r in range(len(labels)):
            if ids[r] < 0:
                ids[r] = shown.shape[0]
                shown = np.vstack([shown, np.zeros((1, n_total), dtype=bool)])
                if k:
                    counts["new_ids_after_first"] += 1
        proposed = np.zeros_like(shown)
        for r, sid in enumerate(ids):
            proposed[sid] |= rows[r]
        # Only audio an earlier update already showed can be locked; newer audio is shown first.
        lock_frame = 0 if lock is None else min(n_prev, max(0, frames(t - lock)))
        for j, (a, b) in enumerate(turn_frames):
            if a >= n_prev:
                continue  # not shown before this update
            before, after = turn_label(shown, a, b), turn_label(proposed, a, b)
            if b <= lock_frame:
                counts["locked_checks"] += 1
                if before != after:
                    counts["locked_changes"] += 1
                    locked_turns_changed.add(j)
            else:
                counts["provisional_checks"] += 1
                counts["provisional_changes"] += before != after
        shown[:, lock_frame:n] = proposed[:, lock_frame:n]
        for j, (a, b) in enumerate(turn_frames):
            if a < n:
                label = turn_label(shown, a, b)
                if not history[j] or history[j][-1][1] != label:
                    history[j].append((t, label))
        n_prev = n
    final = to_segments(shown, n_total)
    score = speaker_time(turns, final, duration)
    # Map shown IDs one-to-one to known speakers on the final display, to judge first labels.
    speakers = sorted({t["speaker_id"] for t in turns})
    truth = matrix(turns, speakers, n_total)
    common = (truth[:, None, :] & shown[None, :, :]).sum(axis=2)
    ti, si = linear_sum_assignment(common, maximize=True)
    right = {int(s): speakers[i] for i, s in zip(ti, si) if common[i, s] > 0}
    settle, first_right = [], 0
    for j, turn in enumerate(turns):
        if not history[j]:
            continue
        settle.append(max(0.0, history[j][-1][0] - turn["end_seconds"]) if len(history[j]) > 1 else 0.0)
        first_right += right.get(history[j][0][1]) == turn["speaker_id"]
    return {**counts, "turns": len(turns), "locked_turns_changed": len(locked_turns_changed),
            "settle_seconds": settle, "first_label_right": first_right, "updates": len(updates),
            "final": {k: score[k] for k in ("labels", "reference_s", "miss_s", "false_alarm_s", "confusion_s",
                                            "error_rate")}}


def pooled(rows):
    keys = ("turns", "locked_checks", "locked_changes", "locked_turns_changed", "provisional_checks",
            "provisional_changes", "merges", "new_ids_after_first", "first_label_right", "updates")
    out = {k: sum(r[k] for r in rows) for k in keys}
    ref = sum(r["final"]["reference_s"] for r in rows)
    err = sum(r["final"]["miss_s"] + r["final"]["false_alarm_s"] + r["final"]["confusion_s"] for r in rows)
    settle = sorted(s for r in rows for s in r["settle_seconds"])
    out.update({
        "locked_change_rate": out["locked_changes"] / out["locked_checks"] if out["locked_checks"] else None,
        "provisional_change_rate": (out["provisional_changes"] / out["provisional_checks"]
                                    if out["provisional_checks"] else None),
        "first_label_right_rate": out["first_label_right"] / out["turns"],
        "live_error_rate": err / ref,
        "settle_median_s": statistics.median(settle),
        "settle_p90_s": settle[math.ceil(0.9 * len(settle)) - 1],
        "settle_max_s": settle[-1],
        "turns_settling_after": {str(s): sum(x > s for x in settle) for s in (0, 15, 30, 60, 120)},
    })
    return out


def main():
    fixtures, prefixes = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text())
    report = {"model_revision": prefixes["model_revision"], "step_seconds": prefixes["step_seconds"],
              "load_seconds": prefixes["load_seconds"], "min_match_seconds": MIN_MATCH, "cases": {}, "pooled": {}}
    for case in (*SCRIPTED, *CONTROLS):
        data = prefixes["cases"][case]
        turns = json.loads((fixtures / case / "segments.json").read_text())
        runs, duration = data["runs"], data["duration_seconds"]
        whole = speaker_time(turns, runs[-1]["segments"], duration)
        row = {"duration_seconds": duration, "speakers": len({t["speaker_id"] for t in turns}),
               "whole_run": {"labels": whole["labels"], "error_rate": whole["error_rate"],
                             "error_s": whole["miss_s"] + whole["false_alarm_s"] + whole["confusion_s"],
                             "reference_s": whole["reference_s"]},
               "diarize_seconds": [[r["prefix_seconds"], r["diarize_seconds"]] for r in runs], "settings": {}}
        for interval in INTERVALS:
            for lock in LOCKS:
                row["settings"][f"{interval}/{lock}"] = simulate(runs, turns, duration, interval, lock)
        report["cases"][case] = row
    by_count = {f"scripted-{n}-speakers": tuple(c for c in SCRIPTED if report["cases"][c]["speakers"] == n)
                for n in (1, 2, 3, 4)}
    for group, names in (("scripted", SCRIPTED), *by_count.items(), ("controls", CONTROLS)):
        rows = {name: report["cases"][name] for name in names}
        ref = sum(r["whole_run"]["reference_s"] for r in rows.values())
        report["pooled"][group] = {
            "whole_run_error_rate": sum(r["whole_run"]["error_s"] for r in rows.values()) / ref,
            "settings": {key: pooled([r["settings"][key] for r in rows.values()])
                         for key in next(iter(rows.values()))["settings"]},
        }
    for row in report["cases"].values():
        for setting in row["settings"].values():
            setting["settle_seconds"] = [round(s, 2) for s in setting["settle_seconds"]]
    json.dump(report, sys.stdout, indent=1, sort_keys=True)
    print()


if __name__ == "__main__":
    main()
