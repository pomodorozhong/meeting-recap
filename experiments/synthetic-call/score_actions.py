"""Inspect anonymized synthetic action predictions or replay verdicts bound to a particular set of outputs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import median

from score_speakers import load, sha256

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE / "action-scripts"
MODES = ("exact-ordinary", "exact-focused", "audio-ordinary", "audio-focused")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def unknown(value):
    return value is None or str(value).strip().casefold() in {"", "unknown", "null", "未指定", "未定", "不明"}


def read_case(root, script):
    gold = load(script)
    run = root / script.stem
    meta = load(run / "case.json")
    if meta["script_sha256"] != sha256(script):
        raise ValueError(f"script changed: {script.stem}")
    packet, orders = {}, {}
    bindings = {"script": meta["script_sha256"], "audio": meta["audio_sha256"],
                "mapping": meta["audio_speaker_map"]}
    runs = dict(meta["runs"])
    diagnostic = run / "labels-focused/run.json"
    if diagnostic.is_file():
        runs["labels-focused"] = load(diagnostic)
    for mode in runs:
        folder = run / mode
        lines, items = load(folder / "lines.json"), load(folder / "items.json")
        pair = [sha256(folder / "lines.json"), sha256(folder / "items.json")]
        if pair != [runs[mode][k] for k in ("lines_sha256", "items_sha256")]:
            raise ValueError(f"changed benchmark output: {folder}")
        bindings[mode] = pair
        names = meta["audio_speaker_map"] if mode.startswith("audio-") else {f"Speaker {k}": k for k in gold["speakers"]}
        orders[mode] = []
        for item in items:
            value = item.get("owner")
            label = f"Speaker {value}" if isinstance(value, str) and value in gold["speakers"] else value
            owner = None if unknown(value) else names.get(str(label), "unmapped")
            stamps = item.get("evidence")
            stamps = [str(s).strip("[] ") for s in stamps] if isinstance(stamps, list) else []
            cited = {s: [line for line in lines if line.startswith(f"[{s}] ")] for s in stamps}
            row = {"prediction": item, "mapped_owner": owner, "cited_lines": cited}
            key = fingerprint([script.stem, row])[:16]
            if key in packet and row != packet[key]:
                raise ValueError("prediction hash collision")
            packet[key] = row
            orders[mode].append(key)
    return gold["actions"], packet, orders, fingerprint(bindings)


def count_items(gold, packet, order, judgments):
    expected = {a["id"]: a for a in gold}
    matched, owners, dates, fields, strict = set(), set(), set(), set(), set()
    totals = Counter(gold=len(gold), emitted=len(order))
    for key in order:
        row = packet[key]
        mark = judgments[key]
        target = mark["target"]
        if target is not None and target not in expected:
            raise ValueError(f"unknown gold ID {target}: {key}")
        if type(mark["due_ok"]) is not bool or type(mark["evidence_ok"]) is not bool:
            raise ValueError(f"expected boolean verdicts: {key}")
        cited = row["cited_lines"]
        valid = bool(cited) and all(cited.values())
        totals["valid_citation_rows"] += valid
        if target is None:
            continue
        matched.add(target)
        owner_ok = row["mapped_owner"] == expected[target]["owner"]
        due_unknown = unknown(row["prediction"].get("due"))
        due_ok = due_unknown if expected[target]["due"] is None else (not due_unknown and mark["due_ok"])
        if owner_ok:
            owners.add(target)
        if due_ok:
            dates.add(target)
        if owner_ok and due_ok:
            fields.add(target)
            if valid and mark["evidence_ok"]:
                strict.add(target)
    totals.update(task_hits=len(matched), owner_hits=len(owners), deadline_hits=len(dates),
                  field_hits=len(fields), strict_hits=len(strict))
    return dict(totals)


def summarize(counts):
    hit, emitted, gold = (counts[k] for k in ("strict_hits", "emitted", "gold"))
    return {**counts, "false_positives": emitted-hit, "misses": gold-hit,
            "precision": hit/emitted if emitted else None, "recall": hit/gold if gold else None,
            "f1": 2*hit/(emitted+gold) if emitted+gold else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inspect", "score"])
    parser.add_argument("results", type=Path)
    parser.add_argument("--case")
    parser.add_argument("--verdicts", type=Path, default=HERE / "reference/action-verdicts.json")
    args = parser.parse_args()
    overall = {m: Counter() for m in (*MODES, "labels-focused")}
    cases, inputs = {}, {}
    times = {m: [] for m in overall}
    peaks = {m: [] for m in overall}
    verdicts = load(args.verdicts) if args.command == "score" else {}
    scripts = [s for s in sorted(SCRIPTS.glob("*.json")) if args.case in (None, s.stem)]
    if not scripts:
        parser.error("unknown case")
    for script in scripts:
        gold, packet, orders, binding = read_case(args.results, script)
        if args.command == "inspect":
            cases[script.stem] = {"binding": binding, "gold": gold, "predictions": dict(sorted(packet.items()))}
            continue
        if set(orders) != set(overall):
            raise ValueError(f"{script.stem}: missing registered conditions")
        case = verdicts[script.stem]
        if binding != case["binding"] or set(case["rows"]) != set(packet):
            raise ValueError(f"{script.stem}: these verdicts do not describe these model outputs")
        folder = args.results / script.stem
        meta = load(folder / "case.json")
        stages = load(folder / "pipeline/stages.json")
        inputs[script.stem] = {k: meta[k] for k in ("script_sha256", "audio_sha256", "duration_seconds")}
        inputs[script.stem]["transcript_pipeline_seconds"] = stages["total"]["seconds"]
        run_stats = {**meta["runs"], "labels-focused": load(folder / "labels-focused/run.json")}
        paired = zip(load(folder / "audio-focused/lines.json"), load(folder / "labels-focused/lines.json"), strict=True)
        inputs[script.stem]["changed_line_labels"] = sum(a != b for a, b in paired)
        inputs[script.stem]["same_actions_after_relabeling"] = (
            run_stats["audio-focused"]["items_sha256"] == run_stats["labels-focused"]["items_sha256"])
        cases[script.stem] = {}
        for mode, order in orders.items():
            counts = count_items(gold, packet, order, case["rows"])
            overall[mode].update(counts)
            timing = run_stats[mode]
            times[mode].append(timing["wall_seconds"])
            peaks[mode].append(timing["peak_footprint_bytes"])
            cases[script.stem][mode] = {**summarize(counts), "wall_seconds": timing["wall_seconds"],
                                       "peak_footprint_bytes": timing["peak_footprint_bytes"]}
    result = {"cases": cases}
    if args.command == "score":
        result["inputs"] = inputs
        result["micro"] = {m: {**summarize(c), "median_seconds": median(times[m]),
                               "total_seconds": round(sum(times[m]), 2), "max_peak_footprint_bytes": max(peaks[m])}
                           for m, c in overall.items()}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
