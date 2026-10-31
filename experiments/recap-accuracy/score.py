#!/usr/bin/env python3
"""Score one pipeline recap of the synthetic call against key.json, using a hand-made matches file.

usage: score.py RUN_DIR MATCHES.json [--json]

RUN_DIR holds the run's summary.json (with parsed "notes") and transcript.md. MATCHES.json says, for each
recap item ("decisions/0", ...), which key items it states and a verdict:
  correct    true, and in a section the key accepts
  misplaced  true, but in a section the key does not accept for it (an assignment listed only as a decision)
  wrong      contradicts the call: a wrong fact, an invented task, or an answered question listed as open
  duplicate  repeats an item already counted in the same recap
Owners are checked automatically against the key; `due_ok` records whether a stated deadline is right.
Topics are not scored.
"""
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent / "synthetic-call" / "reference" / "transcript.json"
SECTIONS = ("decisions", "action_items", "proposals", "open_questions")
VERDICTS = {"correct", "misplaced", "wrong", "duplicate"}


def seconds(stamp):
    h, m, s = (int(x) for x in stamp.split(":"))
    return h * 3600 + m * 60 + s


def line_spans(transcript):
    """Start and end second of each transcript line, keyed by its HH:MM:SS stamp; a line ends where the next starts."""
    starts = [m.group(1) for m in re.finditer(r"^\*\*\[(\d\d:\d\d:\d\d)\] ", transcript, flags=re.M)]
    spans = {}
    for i, stamp in enumerate(starts):
        end = seconds(starts[i + 1]) if i + 1 < len(starts) else float("inf")
        start = seconds(stamp)
        spans[stamp] = (start, max(end, start + 1))
    return spans


def owner(value, names=None):
    """The script speaker (A, B, C) a recap's owner names; `names` undoes a relabeled transcript's names."""
    if value is None or not str(value).strip():
        return None
    value = str(value).strip()
    if names and value in names:
        return names[value]
    match = re.fullmatch(r"(?:Speaker\s*)?([A-Z])", value)
    return match.group(1) if match else value


def score(run_dir, matches):
    key = json.loads((HERE / "key.json").read_text())
    items = {item["id"]: item for item in key["items"]}
    answered = {item["id"] for item in key["answered"]}
    turns = json.loads(REFERENCE.read_text())["segments"]
    notes = json.loads((Path(run_dir) / "summary.json").read_text())["notes"]
    spans = line_spans((Path(run_dir) / "transcript.md").read_text())
    names_path = Path(run_dir) / "names.json"
    names = json.loads(names_path.read_text()) if names_path.exists() else None

    recap = {f"{section}/{i}": item for section in SECTIONS for i, item in enumerate(notes[section])}
    missing = sorted(set(recap) - set(matches["items"]))
    extra = sorted(set(matches["items"]) - set(recap))
    if missing or extra:
        raise ValueError(f"matches must judge every recap item exactly: missing {missing}, unknown {extra}")

    counts = {v: 0 for v in VERDICTS}
    found, placed, evidenced, owners, dues, errors = set(), set(), set(), [], [], []
    for ref, judged in matches["items"].items():
        verdict = judged["verdict"]
        if verdict not in VERDICTS:
            raise ValueError(f"{ref}: unknown verdict {verdict}")
        counts[verdict] += 1
        section = ref.split("/")[0]
        ids = judged.get("matches", [])
        for i in ids:
            if i not in items and i not in answered:
                raise ValueError(f"{ref}: unknown key item {i}")
        if verdict == "wrong":
            errors.append(f"{ref}: {judged.get('note', '')}")
            continue
        if verdict == "duplicate":
            continue
        cited = [spans[e] for e in recap[ref].get("evidence", []) if e in spans]
        for i in ids:
            if i in answered:
                continue
            found.add(i)
            if verdict == "correct" and section in items[i]["accept"]:
                placed.add(i)
            key_turns = [(turns[t]["start"], turns[t]["end"]) for t in items[i]["turns"]]
            if any(a < te and ts < b for a, b in cited for ts, te in key_turns):
                evidenced.add(i)
            if section == "action_items" and i.startswith("T"):
                given, wanted = owner(recap[ref].get("owner"), names), items[i]["owner"]
                owners.append((ref, i, given, wanted, given == wanted))
                due_given = bool(str(recap[ref].get("due") or "").strip())
                if items[i]["due"] is None:
                    dues.append((ref, i, not due_given))
                else:
                    dues.append((ref, i, due_given and judged.get("due_ok", False)))
    key_ids = [i for i in items]
    return {
        "recap_items": len(recap),
        "verdicts": counts,
        "key_items": len(key_ids),
        "found": sorted(found, key=key_ids.index),
        "missed": [i for i in key_ids if i not in found],
        "placed_correctly": len(placed),
        "evidence_covers_item": len(evidenced),
        "owners_right": sum(ok for *_, ok in owners), "owners_checked": len(owners),
        "owner_errors": [f"{ref} ({i}): owner {g}, should be {w}" for ref, i, g, w, ok in owners if not ok],
        "dues_right": sum(ok for *_, ok in dues), "dues_checked": len(dues),
        "errors": errors,
    }


def main():
    run_dir, matches_path = sys.argv[1], sys.argv[2]
    result = score(run_dir, json.loads(Path(matches_path).read_text()))
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    n = result["key_items"]
    print(f"key items found:         {len(result['found'])}/{n} (missed: {', '.join(result['missed']) or 'none'})")
    print(f"  in an accepted section:{result['placed_correctly']:>3}/{n}")
    print(f"  evidence cites them:   {result['evidence_covers_item']:>3}/{len(result['found'])}")
    print(f"recap items:             {result['recap_items']} ({', '.join(f'{k} {v}' for k, v in sorted(result['verdicts'].items()))})")
    print(f"action owners right:     {result['owners_right']}/{result['owners_checked']}")
    print(f"deadlines right:         {result['dues_right']}/{result['dues_checked']}")
    for line in result["owner_errors"] + result["errors"]:
        print(f"  - {line}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        sys.exit(str(error))
