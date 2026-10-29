"""Speaker-order LCS metric extracted from the original experiment; no embedded references.

This is a diagnostic turn-order measure, not DER or an identity-recognition accuracy.
"""
import itertools
import math

from common import segments


def lcs(a, b):
    previous = [0] * (len(b) + 1)
    for x in a:
        row = [0]
        for j, y in enumerate(b):
            row.append(previous[j] + 1 if x == y else max(previous[j + 1], row[j]))
        previous = row
    return previous[-1]


def clip_turns(segs, start, end, min_overlap=0.3):
    seq = []
    for s in sorted(segs, key=lambda s: s["start_seconds"]):
        overlap = min(end, s["end_seconds"]) - max(start, s["start_seconds"])
        if overlap >= min_overlap and (not seq or seq[-1] != s["speaker_id"]):
            seq.append(s["speaker_id"])
    return seq


def score(segs, clips, min_overlap=0.3, mapping=None):
    segments(segs)
    predictions = [clip_turns(segs, max(0, c["start_seconds"] - c.get("padding_seconds", 1)),
                              c["end_seconds"] + c.get("padding_seconds", 1), min_overlap) for c in clips]
    labels = sorted({label for seq in predictions for label in seq if label != "__unassigned__"})
    people = sorted({person for clip in clips for person in clip["speaker_order"]})

    def calculate(candidate):
        details = []
        for clip, seq in zip(clips, predictions):
            # None is an unmapped label, which must not match a reference identity.
            predicted = [candidate.get(label) for label in seq]
            reference = clip["speaker_order"]
            recovered = lcs(predicted, reference)
            correct = (recovered == len(reference) and set(predicted) <= set(reference)
                       and (clip.get("allow_extra_turns", False) or len(predicted) == len(reference)))
            details.append({"item_id": clip["id"], "reference": reference, "predicted": predicted,
                            "raw_labels": seq, "turns_recovered": recovered, "correct": correct})
        return sum(d["turns_recovered"] for d in details), sum(d["correct"] for d in details), details

    if mapping is None:
        # Preserve the historical best-mapping rule, with a bound on factorial searches.
        count = sum(math.comb(len(labels), k) * math.perm(len(people), k)
                    for k in range(min(len(labels), len(people)) + 1))
        if count > 100_000:
            raise ValueError("too many label mappings; supply an explicit per-run mapping JSON")
        best, mapping = None, {}
        for k in range(min(len(labels), len(people)) + 1):
            for chosen in itertools.combinations(labels, k):
                for order in itertools.permutations(people, k):
                    candidate = dict(zip(chosen, order))
                    result = calculate(candidate)
                    if best is None or result[:2] > best[:2]:
                        best, mapping = result, candidate
        recovered, correct, details = best
        mapping_method = "best_reference_mapping"
    else:
        recovered, correct, details = calculate(mapping)
        mapping_method = "explicit"
    return {"metric": "speaker_order_lcs", "version": 1, "min_overlap_seconds": min_overlap,
            "turns_recovered": recovered, "reference_turns": sum(len(c["speaker_order"]) for c in clips),
            "clips_correct": correct, "clips": len(clips), "mapping": mapping,
            "mapping_method": mapping_method, "details": details}
