#!/usr/bin/env python3
"""Score a pipeline run of the synthetic call against the call's known speakers.

usage: score_speakers.py RUN_DIR [REFERENCE_DIR] [--json]

REFERENCE_DIR defaults to experiments/synthetic-call/reference. Two measures, both over characters:

  diarization  Each Whisper word is labelled twice at its own time: by the run's diarization and by the
               known turns. Agreement counts characters whose labels match under the best label mapping.
               Whisper's word times are taken as right, so this isolates the diarizer's errors.
  transcript   The transcript's characters are aligned to the script's text (OpenCC t2s, punctuation and
               spaces dropped). Agreement counts aligned characters whose speaker matches, using the
               same mapping. Text that Whisper put in the wrong turn counts as an error here.

The best mapping sends each diarization label to the known speaker it shares most characters with, so two
labels may map to one speaker, as when a voice is split. It flatters every run equally.
"""
import collections
import difflib
import json
from pathlib import Path
import re
import sys

import pipeline

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parents[1] / "synthetic-call" / "reference"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def characters(text):
    return len(text.strip())


def diarization_agreement(asr, segments, truth):
    pairs = collections.Counter()
    for start, end, text in pipeline.words(asr):
        n = characters(text)
        if n:
            pairs[(pipeline.label_at(segments, start, end) or pipeline.UNASSIGNED,
                   pipeline.label_at(truth, start, end) or pipeline.UNASSIGNED)] += n
    best = {}
    for (label, speaker), n in pairs.items():
        if n > best.get(label, (None, 0))[1]:
            best[label] = (speaker, n)
    mapping = {label: speaker for label, (speaker, _) in best.items()}
    total = sum(pairs.values())
    right = sum(n for (label, speaker), n in pairs.items() if mapping[label] == speaker)
    per_label = collections.Counter()
    for (label, _), n in pairs.items():
        per_label[label] += n
    return mapping, {"characters": total, "agree": right, "rate": right / total if total else 0.0,
                     "characters_per_label": dict(per_label)}


def transcript_agreement(turns, script, mapping, simplify):
    def flatten(rows, key, names=None):
        text, who = [], []
        for row in rows:
            for c in re.sub(r"[\W_]", "", simplify(row["text"]).lower()):
                text.append(c)
                who.append(names.get(row[key], "?") if names else row[key])
        return "".join(text), who

    ref_text, ref_who = flatten(script, "speaker")
    run_text, run_who = flatten(turns, "speaker_id", mapping)
    matcher = difflib.SequenceMatcher(None, ref_text, run_text, autojunk=False)
    aligned = agree = 0
    errors = collections.Counter()
    for a, b, size in matcher.get_matching_blocks():
        for k in range(size):
            aligned += 1
            if ref_who[a + k] == run_who[b + k]:
                agree += 1
            else:
                errors[f"{ref_who[a + k]}->{run_who[b + k]}"] += 1
    return {"script_characters": len(ref_text), "transcript_characters": len(run_text), "aligned": aligned,
            "agree": agree, "rate": agree / aligned if aligned else 0.0, "errors": dict(sorted(errors.items()))}


def score(run_dir, reference_dir=REFERENCE, simplify=None):
    if simplify is None:
        from opencc import OpenCC

        simplify = OpenCC("t2s").convert
    run_dir, reference_dir = Path(run_dir), Path(reference_dir)
    manifest = load(reference_dir / "manifest.json")
    run = load(run_dir / "run.json")
    if run["input_sha256"] != manifest["call_sha256"]:
        raise ValueError("the run's input is not the call this reference describes; regenerate the call with "
                         "the reference's seed, or score against your own out/<script> files")
    truth = load(reference_dir / "segments.json")
    truth = truth["segments"] if isinstance(truth, dict) else truth
    turns = load(run_dir / "turns.json")
    mapping, diarization = diarization_agreement(load(run_dir / "asr.json"), load(run_dir / "diarization.json"),
                                                 truth)
    transcript = transcript_agreement(turns, load(reference_dir / "transcript.json")["segments"], mapping, simplify)
    return {"diarizer": run.get("diarizer", "sortformer"), "mapping": mapping, "labels": len(mapping),
            "turns": len(turns), "script_turns": len(truth), "diarization": diarization, "transcript": transcript}


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    if not args:
        sys.exit(__doc__)
    result = score(*args)
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    d, t = result["diarization"], result["transcript"]
    print(f"diarizer: {result['diarizer']}; labels {result['labels']} {result['mapping']}; "
          f"turns {result['turns']} (script {result['script_turns']})")
    print(f"diarization agreement: {d['rate']:.1%} of {d['characters']} characters")
    print(f"transcript agreement:  {t['rate']:.1%} of {t['aligned']} aligned characters "
          f"(script {t['script_characters']}, transcript {t['transcript_characters']})")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        sys.exit(str(error))
