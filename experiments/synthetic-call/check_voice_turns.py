"""Score how well Whisper understands each voice, turn by turn, in a set of generated collection calls.

Usage: uv run check_voice_turns.py FOLDER [--output REPORT.json]
FOLDER holds generated calls in the collection's layout (<call>/turns/NN-S.wav, manifest.json),
such as the collection itself or a re-voiced copy from generate_audio8.py. Every scripted turn is
decoded on its own with the English-word gate's Whisper model and settings, in the script's
language. Per voice it reports the English terms recovered in Mandarin turns (a term counts when
the decode holds it as a whole word, ignoring case and a space or hyphen inside it, so
"Time Out" is "timeout" and "multi stage" is "multi-stage"), the Mandarin character error rate and the English word error rate.
"""
import argparse
import json
from pathlib import Path
import re

from check_voice import MODEL, REVISION
from collection import SCRIPTS
from score_transcripts import edit_distance, normalizers

TERM = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[.+#-][A-Za-z0-9]+)*")


def english_terms(text):
    """The Latin-letter terms in a Mandarin line."""
    return TERM.findall(text)


def heard(term, decoded):
    """Whether the decode holds the term as a whole word, ignoring case and a space or hyphen inside it."""
    letters = [re.escape(c) for c in term.lower() if c not in " -"]
    pattern = r"(?<![a-z0-9])" + r"[\s-]?".join(letters) + r"(?![a-z0-9])"
    return bool(re.search(pattern, decoded.lower()))


def summarize(turns):
    """Add up per-turn results into per-voice rates and term counts."""
    voices = {}
    for turn in turns:
        voice = voices.setdefault(turn["voice"], {"zh_errors": 0, "zh_units": 0, "en_errors": 0,
                                                  "en_units": 0, "terms": 0, "terms_heard": 0})
        voice[f"{turn['language']}_errors"] += turn["errors"]
        voice[f"{turn['language']}_units"] += turn["units"]
        voice["terms"] += len(turn["terms"])
        voice["terms_heard"] += sum(turn["terms"].values())
    for voice in voices.values():
        voice["zh_cer"] = voice["zh_errors"] / voice["zh_units"] if voice["zh_units"] else None
        voice["en_wer"] = voice["en_errors"] / voice["en_units"] if voice["en_units"] else None
    return voices


def check(folder):
    import mlx_whisper
    from huggingface_hub import snapshot_download

    model = snapshot_download(repo_id=MODEL, revision=REVISION, allow_patterns=["config.json", "weights.npz"])
    normalize = normalizers()
    turns = []
    for name, script_path in SCRIPTS.items():
        if not (folder / name / "manifest.json").is_file():
            continue
        script = json.loads(script_path.read_text(encoding="utf-8"))
        language = script.get("language", "zh")
        for number, turn in enumerate(script["turns"], 1):
            path = folder / name / "turns" / f"{number:02d}-{turn['speaker']}.wav"
            decoded = mlx_whisper.transcribe(str(path), path_or_hf_repo=model, language=language,
                                             temperature=0.0, condition_on_previous_text=False)["text"].strip()
            reference = normalize[language](turn["text"])
            terms = english_terms(turn["text"]) if language == "zh" else []
            turns.append({"call": name, "turn": number, "voice": script["speakers"][turn["speaker"]]["voice"],
                          "language": language, "text": turn["text"], "decoded": decoded,
                          "errors": edit_distance(reference, normalize[language](decoded)),
                          "units": len(reference), "terms": {term: heard(term, decoded) for term in terms}})
        print(f"{name}: {len(script['turns'])} turns decoded", flush=True)
    return {"folder": str(folder), "model": {"repository": MODEL, "revision": REVISION},
            "settings": {"temperature": 0.0, "condition_on_previous_text": False, "language": "the script's"},
            "voices": summarize(turns), "turns": turns}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--output", type=Path, help="report path (default: FOLDER/voice-turns.json)")
    args = parser.parse_args()
    report = check(args.folder)
    output = args.output or args.folder / "voice-turns.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for voice, result in sorted(report["voices"].items()):
        cer = "" if result["zh_cer"] is None else f" Mandarin CER {result['zh_cer']:.1%}"
        wer = "" if result["en_wer"] is None else f" English WER {result['en_wer']:.1%}"
        print(f"{voice}: terms {result['terms_heard']}/{result['terms']}{cer}{wer}")
    print(f"report: {output}")


if __name__ == "__main__":
    main()
