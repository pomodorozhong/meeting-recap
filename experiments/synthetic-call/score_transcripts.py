"""Report English WER and Mandarin CER separately for every scripted call.

Run with FIXTURES_ROOT RUNS_ROOT, where each run has <call>/asr.json.
An optional --baseline report fails if either language's error rate regresses.
"""
import argparse
from importlib.metadata import version
import json
import math
from pathlib import Path

from collection import SCRIPTS, digest, load


def transcript_text(payload):
    if not isinstance(payload, dict):
        raise ValueError("ASR must be a text or segments object")
    if isinstance(payload.get("text"), str):
        return payload["text"]
    segments = payload["segments"]
    if not isinstance(segments, list) or any(not isinstance(s, dict) or not isinstance(s.get("text"), str) for s in segments):
        raise ValueError("ASR segments must contain text strings")
    return " ".join(segment["text"] for segment in segments)


def edit_distance(reference, hypothesis):
    previous = list(range(len(hypothesis) + 1))
    for index, expected in enumerate(reference, 1):
        current = [index]
        for column, actual in enumerate(hypothesis, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (expected != actual)))
        previous = current
    return previous[-1]


def normalizers():
    from opencc import OpenCC
    from transformers.models.whisper.english_normalizer import EnglishTextNormalizer

    english = EnglishTextNormalizer({})
    chinese = OpenCC("t2s")
    return {"en": lambda text: english(text).split(),
            "zh": lambda text: [c for c in chinese.convert(text).lower() if c.isalnum()]}


def score(fixtures, runs):
    normalize = normalizers()
    groups = {language: {"metric": metric, "errors": 0, "reference_units": 0, "calls": 0}
              for language, metric in (("en", "wer"), ("zh", "cer"))}
    references, cases = {}, {}
    for name, script_path in SCRIPTS.items():
        script = load(script_path)
        language = script.get("language", "zh")
        if language not in groups:
            raise ValueError(f"unsupported language for {name}: {language}")
        folder = fixtures / name
        manifest = load(folder / "manifest.json")
        audio_hash = digest(folder / "call.wav")
        if manifest["call_sha256"] != audio_hash:
            raise ValueError(f"{name}/call.wav differs from its manifest")
        if manifest.get("language", "zh") != language:
            raise ValueError(f"{name} has inconsistent language metadata")
        reference_path = folder / "transcript.json"
        reference_text = transcript_text(load(reference_path))
        asr_path = runs / name / "asr.json"
        asr = load(asr_path)
        if asr.get("audio_sha256", audio_hash) != audio_hash:
            raise ValueError(f"{name}/asr.json describes different audio")
        hypothesis_text = transcript_text(asr)
        reference = normalize[language](reference_text)
        hypothesis = normalize[language](hypothesis_text)
        if not reference:
            raise ValueError(f"{name} has no reference units")
        errors = edit_distance(reference, hypothesis)
        cases[name] = {"language": language, "metric": groups[language]["metric"],
                       "errors": errors, "reference_units": len(reference),
                       "rate": errors / len(reference), "asr_sha256": digest(asr_path)}
        references[name] = {"language": language, "call_sha256": audio_hash,
                            "transcript_sha256": digest(reference_path)}
        groups[language]["errors"] += errors
        groups[language]["reference_units"] += len(reference)
        groups[language]["calls"] += 1
    for language, group in groups.items():
        if not group["calls"]:
            raise ValueError(f"missing language coverage: {language}")
        group["rate"] = group["errors"] / group["reference_units"]
    versions = {
        "en": {"implementation": "transformers Whisper EnglishTextNormalizer",
               "spelling_map": "empty", "version": version("transformers")},
        "zh": {"implementation": "OpenCC t2s, lowercase alphanumeric characters",
               "version": version("opencc-python-reimplemented")},
    }
    return {"groups": groups, "calls": cases, "references": references,
            "normalizers": versions}


def compare(current, baseline, maximum_regression=0.0):
    if not math.isfinite(maximum_regression) or maximum_regression < 0:
        raise ValueError("maximum regression must be finite and nonnegative")
    if (current["references"] != baseline["references"]
            or current["normalizers"] != baseline["normalizers"]):
        raise ValueError("baseline uses different audio, transcripts or normalization")
    if set(baseline.get("groups", {})) != {"en", "zh"}:
        raise ValueError("baseline requires both English WER and Mandarin CER")
    results = {}
    for language in ("en", "zh"):
        actual = current["groups"][language]["rate"]
        previous = baseline["groups"][language]["rate"]
        delta = actual - previous
        results[language] = {"baseline": previous, "current": actual, "delta": delta,
                             "passed": delta <= maximum_regression + 1e-12}
    return {"passed": all(result["passed"] for result in results.values()),
            "maximum_regression": maximum_regression, "languages": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", type=Path)
    parser.add_argument("runs", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--maximum-regression", type=float, default=0.0,
                        help="allowed absolute rate increase per language, default 0")
    args = parser.parse_args()
    protected = {args.runs / name / "asr.json" for name in SCRIPTS}
    protected.update(SCRIPTS.values())
    protected.update(args.fixtures / name / filename for name in SCRIPTS
                     for filename in ("call.wav", "manifest.json", "transcript.json", "segments.json"))
    if args.baseline:
        protected.add(args.baseline)
    if args.output.resolve() in {path.resolve() for path in protected}:
        parser.error("the report path must differ from the baseline and input files")
    try:
        report = score(args.fixtures, args.runs)
        if args.baseline:
            report["comparison"] = compare(report, load(args.baseline), args.maximum_regression)
        args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"{error}\n")
    for language, group in report["groups"].items():
        print(f"{language} {group['metric'].upper()} {group['rate']:.2%} "
              f"({group['errors']}/{group['reference_units']}, {group['calls']} calls)")
    return 0 if report.get("comparison", {"passed": True})["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
