"""Build a local web page that plays the same collection calls in several voice versions side by side.

Usage: uv run compare_voices.py OUT LABEL=FOLDER [LABEL=FOLDER ...]
Each FOLDER holds generated calls in the collection's layout (OUT/<call>/call.wav, turns/,
transcript.json), as written by generate.py, generate_lfm3.py or generate_audio8.py. Put the
current collection first: it is the version the others are heard against. OUT gets index.html,
data.js and one link per version, and needs only a static file server, for example
`python3 -m http.server 5207 --bind 127.0.0.1 --directory OUT`. The audio is linked, not copied.
"""
import argparse
import json
from pathlib import Path
import re
import shutil

from check_voice import TERMS, TURN_INDICES

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "compare_voices.html"
LABEL = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")


def parse_versions(pairs):
    """Turn LABEL=FOLDER arguments into an ordered {label: folder} map."""
    versions = {}
    for pair in pairs:
        label, separator, folder = pair.partition("=")
        if not separator or not folder:
            raise ValueError(f"expected LABEL=FOLDER, got {pair!r}")
        if not LABEL.match(label) or label in versions:
            raise ValueError(f"labels must be unique lowercase words with digits or dashes: {label!r}")
        path = Path(folder).expanduser().resolve()
        if not path.is_dir():
            raise ValueError(f"not a folder: {folder}")
        versions[label] = path
    if len(versions) < 2:
        raise ValueError("give at least two versions to compare")
    return versions


def gate_turns(name):
    """Mark the turns the English-word gate checks, so a listener can find them."""
    if name != "handoff":
        return {}
    return {TURN_INDICES[index] + 1: f"gate: “{term}”" for term, index in TERMS.items()}


def voiced_from_script(call):
    """Read a call's manifest if a script was voiced into it, or None for derived recordings."""
    path = call / "manifest.json"
    if not (call / "transcript.json").is_file() or not path.is_file():
        return None
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return manifest if "speakers" in manifest else None


def collect(versions):
    """List every voiced call any version has, with its turns and which versions hold each file.

    Calls that no version voiced from a script, such as the collection's silence, channel and
    overlap recordings, have no turns to compare and are left out.
    """
    names = sorted({call.parent.name for folder in versions.values() for call in folder.glob("*/call.wav")})
    calls = []
    for name in names:
        have = [label for label, folder in versions.items() if (folder / name / "call.wav").is_file()]
        source = next((versions[label] / name for label in have if voiced_from_script(versions[label] / name)), None)
        if source is None:
            continue
        segments = json.loads((source / "transcript.json").read_text(encoding="utf-8"))["segments"]
        manifest = voiced_from_script(source)
        marks = gate_turns(name)
        turns = []
        for number, segment in enumerate(segments, 1):
            file = f"turns/{number:02d}-{segment['speaker']}.wav"
            turns.append({"n": number, "speaker": segment["speaker"], "text": segment["text"], "file": file,
                          "have": [label for label in have if (versions[label] / name / file).is_file()],
                          "mark": marks.get(number, "")})
        durations = {}
        for label in have:
            path = versions[label] / name / "manifest.json"
            if path.is_file():
                durations[label] = json.loads(path.read_text(encoding="utf-8")).get("duration_seconds")
        calls.append({"name": name, "language": manifest.get("language", "zh"), "versions": have,
                      "seconds": durations,
                      "speakers": {speaker: value["voice"] for speaker, value in manifest["speakers"].items()},
                      "turns": turns})
    return calls


def build(out, versions):
    """Write the page, its data and one link per version into OUT, replacing an earlier build."""
    calls = collect(versions)
    if not calls:
        raise ValueError("no call.wav found in any version")
    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():
        if old.is_symlink():
            old.unlink()
        elif old.name in ("index.html", "data.js"):
            old.unlink()
    for label, folder in versions.items():
        (out / label).symlink_to(folder, target_is_directory=True)
    data = {"versions": list(versions), "calls": calls}
    (out / "data.js").write_text("window.COMPARISON = " + json.dumps(data, ensure_ascii=False) + ";\n",
                                 encoding="utf-8")
    shutil.copyfile(TEMPLATE, out / "index.html")
    return calls


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path, help="folder to write the page into")
    parser.add_argument("versions", nargs="+", metavar="LABEL=FOLDER",
                        help="each voice version; the first is the current collection")
    args = parser.parse_args()
    try:
        versions = parse_versions(args.versions)
        calls = build(args.out, versions)
    except ValueError as error:
        parser.error(str(error))
    missing = [f"{call['name']} (no {', '.join(label for label in versions if label not in call['versions'])})"
               for call in calls if len(call["versions"]) < len(versions)]
    print(f"{len(calls)} calls in {args.out}/index.html")
    if missing:
        print("missing in some versions: " + "; ".join(missing))


if __name__ == "__main__":
    main()
