#!/usr/bin/env python3
"""Score who-spoke-when on the synthetic call against its known turns, over characters.

usage: score_speakers.py --asr ASR.json --segments SEGMENTS.json [--turns TURNS.json]
                         (--audio CALL.wav | --audio-sha256 HEX) [--reference DIR] [--json]

Inputs use the formats the runners share (docs/runners.md):
  --asr       WhisperKit-shaped transcript with word timestamps: {"segments": [{"words": [{"word",
              "start", "end"}]}]}
  --segments  the run's diarization: [{"speaker_id", "start_seconds", "end_seconds"}]
  --turns     optional: the run's attached transcript, in the same order as spoken:
              [{"speaker_id", "text"}] (extra keys are ignored)
  --audio or --audio-sha256  the audio the run used; it must be the call reference/manifest.json describes

Two measures:
  diarization  Each Whisper word is labelled twice at its own time: by --segments and by the known turns.
               Agreement counts characters whose labels match under the best label mapping. Whisper's word
               times are taken as right, so this isolates the diarizer's errors.
  transcript   (with --turns) The turns' characters are aligned to the script's text (OpenCC t2s,
               punctuation and spaces dropped). Agreement counts aligned characters whose speaker matches
               under the same mapping, so text placed in the wrong turn counts as an error too.

The best mapping sends each label to the known speaker it shares most characters with, so two labels may
map to one speaker, as when a voice is split. It flatters every run equally.
"""
import argparse
import collections
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
UNASSIGNED = "__unassigned__"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def label_at(segments, start, end):
    """The label overlapping [start, end] the most; else the nearest within 1 s; else None."""
    best, overlap = None, 0.0
    for segment in segments:
        amount = min(end, segment["end_seconds"]) - max(start, segment["start_seconds"])
        if amount > overlap:
            best, overlap = segment["speaker_id"], amount
    if best is None and segments:
        middle = (start + end) / 2
        distance, best = min((min(abs(middle - s["start_seconds"]), abs(middle - s["end_seconds"])), s["speaker_id"])
                             for s in segments)
        if distance > 1:
            best = None
    return best


def words(asr):
    """(start, end, text) for every word, without Whisper's special tokens."""
    for index, segment in enumerate(asr["segments"]):
        if not segment.get("words") and re.sub(r"<\|[^|]*\|>", "", segment.get("text", "")).strip():
            raise ValueError(f"transcript segment {index} has text but no word timestamps; rerun ASR with them")
        for word in segment.get("words") or []:
            text = re.sub(r"<\|[^|]*\|>", "", word["word"])
            if text.strip():
                yield float(word["start"]), float(word["end"]), text


def diarization_agreement(asr, segments, truth):
    pairs = collections.Counter()
    for start, end, text in words(asr):
        pairs[(label_at(segments, start, end) or UNASSIGNED, label_at(truth, start, end) or UNASSIGNED)] += \
            len(text.strip())
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


def score(asr, segments, audio_sha256, turns=None, reference=HERE / "reference", simplify=None):
    reference = Path(reference)
    if audio_sha256 != load(reference / "manifest.json")["call_sha256"]:
        raise ValueError("the run's audio is not the call this reference describes; regenerate the call with "
                         "the reference's seed, or score against your own out/<script> files")
    truth = load(reference / "segments.json")
    truth = truth["segments"] if isinstance(truth, dict) else truth
    mapping, diarization = diarization_agreement(asr, segments, truth)
    result = {"mapping": mapping, "labels": len(mapping), "script_turns": len(truth), "diarization": diarization}
    if turns is not None:
        if simplify is None:
            from opencc import OpenCC

            simplify = OpenCC("t2s").convert
        result["turns"] = len(turns)
        result["transcript"] = transcript_agreement(turns, load(reference / "transcript.json")["segments"], mapping,
                                                    simplify)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--asr", required=True)
    parser.add_argument("--segments", required=True)
    parser.add_argument("--turns")
    audio = parser.add_mutually_exclusive_group(required=True)
    audio.add_argument("--audio")
    audio.add_argument("--audio-sha256")
    parser.add_argument("--reference", default=HERE / "reference")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = score(load(args.asr), load(args.segments), args.audio_sha256 or sha256(args.audio),
                   load(args.turns) if args.turns else None, args.reference)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    d = result["diarization"]
    print(f"labels {result['labels']} {result['mapping']}")
    print(f"diarization agreement: {d['rate']:.1%} of {d['characters']} characters")
    if "transcript" in result:
        t = result["transcript"]
        print(f"transcript agreement:  {t['rate']:.1%} of {t['aligned']} aligned characters "
              f"(script {t['script_characters']}, transcript {t['transcript_characters']}); "
              f"turns {result['turns']} (script {result['script_turns']})")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        sys.exit(str(error))
