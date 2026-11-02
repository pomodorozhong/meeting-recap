"""Check the female handoff voice with the fixed unprompted Whisper gate.

Usage: uv run --project experiments/synthetic-call python \
    experiments/synthetic-call/check_voice.py HANDOFF_FOLDER [--output REPORT.json]
"""
import argparse
import difflib
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "scripts/handoff.json"
MODEL = "mlx-community/whisper-large-v3-mlx"
REVISION = "49e6aa286ad60c14352c404340ded53710378a11"
RATE = 16000
TURN_INDICES = (3, 5, 9)
TERMS = {"log": 1, "timeout": 2}
MIN_MANDARIN_SIMILARITY = 0.65
TURN_TOLERANCE_SECONDS = 0.2


def contains_term(text, term):
    return bool(re.search(r"(?<![a-z0-9])" + term + r"(?![a-z0-9])", text, re.IGNORECASE))


def score_decodes(whole, timed, expected, spans, simplify):
    """Evaluate complete English tokens, Mandarin agreement and word locations."""
    def mandarin(text):
        return "".join(re.findall(r"[\u3400-\u9fff]", simplify(text)))

    text = whole["text"]
    hits = {term: contains_term(text, term) for term in TERMS}
    similarity = difflib.SequenceMatcher(
        None, mandarin(expected), mandarin(text), autojunk=False).ratio()
    timed_hits = {}
    words = [word for segment in timed.get("segments", []) for word in segment.get("words", [])]
    for term, index in TERMS.items():
        start, end = spans[index]
        turn_words = [word for word in words
                      if start - TURN_TOLERANCE_SECONDS <= (word["start"] + word["end"]) / 2
                      <= end + TURN_TOLERANCE_SECONDS]
        turn_text = "".join(word["word"] for word in turn_words)
        timed_hits[term] = {"in_turn": contains_term(turn_text, term), "text": turn_text}
    passed = (all(hits.values()) and similarity >= MIN_MANDARIN_SIMILARITY
              and all(result["in_turn"] for result in timed_hits.values()))
    return {"passed": passed, "text": text, "hits": hits,
            "mandarin_similarity": similarity, "timed": timed_hits}


def check_voice(folder):
    import mlx_whisper
    import numpy as np
    import soundfile as sf
    from huggingface_hub import snapshot_download
    from opencc import OpenCC

    script_bytes = SCRIPT.read_bytes()
    turns = json.loads(script_bytes)["turns"]
    chunks = [np.zeros(RATE // 2, dtype=np.float32)]
    sources, spans, expected = [], [], []
    for index in TURN_INDICES:
        turn = turns[index]
        if turn["speaker"] != "B":
            raise ValueError(f"handoff turn {index + 1} must be speaker B")
        name = f"turns/{index + 1:02d}-B.wav"
        payload = (folder / name).read_bytes()
        audio, rate = sf.read(io.BytesIO(payload), dtype="float32")
        if rate != RATE or audio.ndim != 1 or not len(audio) or not np.isfinite(audio).all():
            raise ValueError(f"{name} must be finite nonempty 16 kHz mono audio")
        if spans:
            chunks.append(np.zeros(round(turn.get("gap_seconds", 0.3) * RATE), dtype=np.float32))
        start = sum(map(len, chunks)) / RATE
        chunks.append(audio)
        spans.append([start, start + len(audio) / RATE])
        sources.append({"file": name, "sha256": hashlib.sha256(payload).hexdigest(),
                        "script_turn": index + 1, "text": turn["text"]})
        expected.append(turn["text"])
    chunks.append(np.zeros(RATE // 2, dtype=np.float32))
    model_path = snapshot_download(repo_id=MODEL, revision=REVISION,
                                   allow_patterns=["config.json", "weights.npz"])
    settings = {"language": "zh", "temperature": 0.0, "condition_on_previous_text": False}
    with tempfile.TemporaryDirectory(prefix="synthetic-voice-check-") as temporary:
        audition = Path(temporary) / "audition.wav"
        sf.write(audition, np.concatenate(chunks), RATE, subtype="PCM_16")
        audition_sha256 = hashlib.sha256(audition.read_bytes()).hexdigest()
        whole = mlx_whisper.transcribe(str(audition), path_or_hf_repo=model_path,
                                        word_timestamps=False, **settings)
        timed = {}
        if all(contains_term(whole["text"], term) for term in TERMS):
            timed = mlx_whisper.transcribe(str(audition), path_or_hf_repo=model_path,
                                           word_timestamps=True, **settings)
    report = score_decodes(whole, timed, "".join(expected), spans, OpenCC("t2s").convert)
    report.update(model={"repository": MODEL, "revision": REVISION}, settings=settings,
                  minimum_mandarin_similarity=MIN_MANDARIN_SIMILARITY,
                  turn_tolerance_seconds=TURN_TOLERANCE_SECONDS,
                  source_script_sha256=hashlib.sha256(script_bytes).hexdigest(),
                  inputs=sources, audition_sha256=audition_sha256,
                  sample_rate=RATE, spans=spans)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="generated handoff folder containing turns/")
    parser.add_argument("--output", type=Path, help="JSON report path (default: HANDOFF_FOLDER/voice-check.json)")
    args = parser.parse_args()
    output = args.output or args.folder / "voice-check.json"
    protected = [SCRIPT, *(args.folder / name for name in ("call.wav", "manifest.json",
                                                        "transcript.json", "segments.json")),
                 *(args.folder / f"turns/{index + 1:02d}-B.wav" for index in TURN_INDICES)]
    if output.resolve() in {path.resolve() for path in protected}:
        parser.error("the report path must differ from the source script and audition inputs")
    try:
        report = check_voice(args.folder)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"{error}\n")
    verdict = "PASS" if report["passed"] else "FAIL"
    print(f"{verdict} log={report['hits']['log']} timeout={report['hits']['timeout']} "
          f"Mandarin={report['mandarin_similarity']:.1%} report={output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
