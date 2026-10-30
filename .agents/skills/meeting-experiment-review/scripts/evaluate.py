#!/usr/bin/env python3
"""Compare registered diarization runs against an immutable confirmed-reference snapshot."""
import argparse
import json
import sys

from common import artifact, dataset, digest, fingerprint, identifier, now, number, private, read_json, run, snapshot, write_new
from scoring import score


def evaluate(root, reference_id, run_ids, evaluation_id, min_overlap=0.3, mappings=None):
    identifier(evaluation_id)
    identifier(reference_id)
    number(min_overlap, "min_overlap", minimum=0.000001)
    reference = read_json(root / "references" / (reference_id + ".json"))
    expected = reference["sha256"]
    if fingerprint({k: v for k, v in reference.items() if k != "sha256"}) != expected:
        raise ValueError("reference snapshot changed")
    built_for = reference.get("source", {}).get("min_overlap_seconds", min_overlap)
    if built_for != min_overlap:
        raise ValueError(f"reference {reference_id} left out turns shorter than {built_for} s; evaluate with --min-overlap {built_for}")
    comparisons = []
    for run_id in run_ids:
        info = run(root, run_id)
        if info["status"] != "completed":
            raise ValueError(f"run {run_id} is {info['status']}; it cannot be scored as completed")
        predicted = artifact(root, info, "segments")
        clips = [c for c in reference["clips"] if c["recording_id"] == info["recording_id"] and c["task"] == "speaker_order"]
        if not clips:
            raise ValueError(f"no confirmed speaker-order references for {run_id}")
        comparisons.append({"run_id": run_id, "recording_id": info["recording_id"], "model": info["model"],
                            "run_sha256": fingerprint(info), "segments_sha256": info["artifacts"]["segments"]["sha256"],
                            **score(predicted, clips, min_overlap, (mappings or {}).get(run_id))})
    # Scores for different recordings or tasks must not be pooled into a misleading ranking.
    sets = {tuple(row["item_id"] for row in result["details"]) for result in comparisons}
    if len(sets) > 1:
        raise ValueError("compare runs on the same recording and identical reference items in one evaluation")
    result = {"format": "meeting-review-evaluation", "version": 1, "id": evaluation_id,
              "created_at": now(), "code": snapshot(root), "reference_id": reference_id, "reference_sha256": expected,
              "excluded": reference["excluded"],
              "other_tasks_not_scored": sum(c["task"] != "speaker_order" for c in reference["clips"]),
              "results": comparisons,
              "limits": "Selected-clip speaker order only; not DER, transcript accuracy, or a population error rate."}
    directory = private(root, root / "evaluations" / evaluation_id)
    if directory.exists():
        raise ValueError("evaluation ID already exists")
    lines = ["# Private evaluation", "", "Speaker-order LCS on the same confirmed clips.", "",
             "| Run | Turns recovered | Clips correct |", "| --- | ---: | ---: |"]
    for item in comparisons:
        lines.append(f"| {item['run_id']} | {item['turns_recovered']}/{item['reference_turns']} | {item['clips_correct']}/{item['clips']} |")
    lines.extend(["", result["limits"], "", f"Reference: {reference_id}; SHA-256: {expected}.",
                  f"Excluded unresolved/skipped/unusable items: {len(reference['excluded'])}.",
                  f"Confirmed items of other tasks not scored: {result['other_tasks_not_scored']}.",
                  "Mappings are fitted to the reference unless an explicit mapping was supplied."])
    directory.mkdir(parents=True)
    with (directory / "report.md").open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    # Sealed like a reference: validate checks the result and the report against these digests.
    result["report_sha256"] = digest(directory / "report.md")
    result = {**result, "sha256": fingerprint(result)}
    write_new(directory / "evaluation.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset")
    parser.add_argument("--reference", required=True)
    parser.add_argument("--runs", nargs="+", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--min-overlap", type=float, default=0.3)
    parser.add_argument("--mappings", help="private JSON: run ID -> prediction label -> reference speaker ID")
    args = parser.parse_args()
    result = evaluate(dataset(args.dataset), args.reference, args.runs, args.id, args.min_overlap,
                      read_json(args.mappings) if args.mappings else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        sys.exit(str(error))
