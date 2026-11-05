"""Run Turbo through the pause option on `onboarding` and check it against the saved split output.

Usage: turbo_pause_check.py FIXTURES RESULTS SPLIT_TURBO [--audio PATH]

FIXTURES is the verified synthetic collection, RESULTS a new absolute folder, and SPLIT_TURBO the
`onboarding/split/turbo.json` written by the digital silence experiment (its `spans.json` must sit beside it).
By default the pipeline reads FIXTURES/onboarding/call.wav; --audio names another copy of that recording.
The pass rule is in docs/experiments/2026-11-05-turbo-pause-check.md. Writes RESULTS/check.json.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from collection import digest, load
from score_transcripts import edit_distance, normalizers, transcript_text

HERE = Path(__file__).resolve().parent
PIPE = HERE.parent / "pipelines" / "whisper-sortformer"
EXPECTED_EDITS = 20
TOLERANCE_SECONDS = 0.001


def words(payload):
    return [(w["word"], w["start"], w["end"]) for s in payload["segments"] for w in s.get("words", [])]


def same_words(got, want):
    if len(got) != len(want):
        return False
    return all(a[0] == b[0] and abs(a[1] - b[1]) <= TOLERANCE_SECONDS and abs(a[2] - b[2]) <= TOLERANCE_SECONDS
               for a, b in zip(got, want))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("fixtures")
    p.add_argument("results")
    p.add_argument("split_turbo")
    p.add_argument("--audio")
    args = p.parse_args()
    results = Path(args.results)
    if not results.is_absolute() or results.exists():
        sys.exit("RESULTS must be a new absolute path")
    fixtures = Path(args.fixtures)
    audio = Path(args.audio) if args.audio else fixtures / "onboarding" / "call.wav"
    split_turbo = Path(args.split_turbo)
    saved_spans = load(split_turbo.parent / "spans.json")

    out = results / "turbo-pause-pipeline"
    results.mkdir(parents=True)
    subprocess.run([PIPE / ".venv/bin/python", PIPE / "recap.py", "run", audio, out, "--asr", "turbo-q4",
                    "--diarizer", "who", "--split-digital-pauses", "--no-summary"],
                   check=True, env={**__import__("os").environ, "HF_HUB_OFFLINE": "1"})

    asr = load(out / "asr.json")
    saved = load(split_turbo)
    reference = normalizers()["zh"](transcript_text(load(fixtures / "onboarding" / "transcript.json")))
    edits = edit_distance(reference, normalizers()["zh"](transcript_text(asr)))
    got, want = words(asr), words(saved)
    transcript = (out / "transcript.md").read_text(encoding="utf-8") if (out / "transcript.md").exists() else ""
    pause_start = saved_spans[0][1] / 16000
    check = {
        "audio_sha256": digest(audio),
        "model_revision": asr.get("model_revision"),
        "spans": asr.get("spans_samples"),
        "saved_spans": saved_spans,
        "words": len(got),
        "saved_words": len(want),
        "edits": edits,
        "words_after_pause": sum(1 for w in got if w[1] >= pause_start),
        "transcript_lines": len([line for line in transcript.splitlines() if line.strip()]),
        "elapsed_seconds": asr.get("elapsed_seconds"),
        "mlx_peak_bytes": asr.get("mlx_peak_bytes"),
    }
    check["pass"] = {
        "two_spans_match": asr.get("spans_samples") == saved_spans,
        "words_and_times_match": same_words(got, want),
        "edits_are_20": edits == EXPECTED_EDITS,
        "transcript_has_lines_on_both_sides": check["words_after_pause"] > 0 and check["transcript_lines"] > 0,
    }
    check["passed"] = all(check["pass"].values())
    (results / "check.json").write_text(json.dumps(check, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(check, indent=2, ensure_ascii=False))
    sys.exit(0 if check["passed"] else 1)


if __name__ == "__main__":
    main()
