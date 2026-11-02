"""Run the remaining registered comparisons after expanded_decode.sh (all inference serial)."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import soundfile as sf

from collection import CONTROLS, HERE, RATE, SCRIPTS, build, digest, load

PIPE = HERE.parent / "pipelines/whisper-sortformer"
MLX = HERE.parent / "mlx"
DIAR = HERE.parent / "diarization"
MODELS = {"whisper": ("mlx-community/whisper-large-v3-mlx", "49e6aa286ad60c14352c404340ded53710378a11"),
          "breeze": ("eoleedi/Breeze-ASR-25-mlx", "172151e3fd93ab6dc841d639f23dd48b24bc8301"),
          "turbo": ("mlx-community/whisper-large-v3-turbo-q4", "660c343bbf4e52ac257f0b7d952e5388e6f93bef")}
ALT_DIGESTS = {"ls-eend": "d375290fbaf031b22ee72cd4539f781bbf0c58add15fc64c457c3be89610ba04",
               "speaker-diarization": "94e171fd88406ba786232eb86860767185a57b47d89bda6dc8dd8b914563dafb"}


def save(path, obj):
    with path.open("x") as handle:
        json.dump(obj, handle, ensure_ascii=False, allow_nan=False)


def timed(out, name, command):
    print(out.name, name, flush=True)
    with (out / (name + ".log")).open("x") as log:
        subprocess.run(["/usr/bin/time", "-l", "-o", out / (name + ".time"), *command], check=True,
                       stdout=log, stderr=subprocess.STDOUT, env={**os.environ, "HF_HUB_OFFLINE": "1"})


def chunks(pcm, rate=RATE):
    """Return half-open sample spans. Keep 250 ms of context bordering each long zero run."""
    active = np.flatnonzero(pcm)
    if not active.size:
        return []
    minimum = 5 * rate
    groups = np.split(active, np.flatnonzero(np.diff(active) > minimum) + 1)
    spans = []
    for group in groups:
        first, last = int(group[0]), int(group[-1] + 1)
        start = 0 if first < minimum else first - rate // 4
        end = len(pcm) if len(pcm) - last < minimum else last + rate // 4
        spans.append((start, end))
    return spans


def split(source, case, lang):
    pcm, rate = sf.read(source / "call.wav", dtype="int16")
    if rate != RATE or pcm.ndim != 1:
        raise ValueError("unexpected audio format")
    spans = chunks(pcm)
    out = case / "split"
    out.mkdir()
    save(out / "spans.json", spans)
    if spans == [(0, len(pcm))]:
        return
    for n, (start, end) in enumerate(spans):
        sf.write(out / f"{n}.wav", pcm[start:end].astype("float32") / 32768, RATE, subtype="FLOAT")
    for model, (repo, revision) in MODELS.items():
        parts = []
        for n, (start, _) in enumerate(spans):
            target = out / f"{model}-{n}.json"
            timed(out, f"{model}-{n}", [MLX / ".venv/bin/python", MLX / "run.py", out / f"{n}.wav",
                                        target, repo, lang, "--revision", revision])
            part = load(target)
            for seg in part["segments"]:
                for item in [seg, *seg["words"]]:
                    item["start"] += start / rate
                    item["end"] += start / rate
            parts.append(part)
        save(out / f"{model}.json", {"text": " ".join(p["text"].strip() for p in parts),
                                      "segments": [s for p in parts for s in p["segments"]]})


def weights():
    # Ask the pipeline to verify its own cache using its locked environment.
    cmd = ('import json, pins; print(json.dumps({**{k:pins.check_weights(k) for k in ("sortformer","who")},'
           '**{k:pins.tree_sha256(pins.SORTFORMER_MODELS.parent / k) for k in ("ls-eend","speaker-diarization")}}))')
    data = json.loads(subprocess.check_output([PIPE / ".venv/bin/python", "-c", cmd], cwd=PIPE))
    if any(data[k] != v for k, v in ALT_DIGESTS.items()):
        raise ValueError("alternative diarizer weights differ from the historical benchmark")
    return data


def diarize(case, verified):
    save(case / "weights.json", verified)
    wav = case / "audio.wav"
    fluid = PIPE / ".build/release/fluidaudiocli"
    who = PIPE / ".build/release/who-diarize"
    who_models = os.environ.get("WHO_MODELS") or Path.home() / "Library/Application Support/meeting-recap/who"
    timed(case, "who", [who, wav, case / "who.json", who_models])
    timed(case, "sortformer", [fluid, "sortformer", wav, "--output", case / "sortformer.raw.json"])
    convert = [sys.executable, DIAR / "sortformer_to_segments.py"]
    subprocess.run([*convert, case / "sortformer.raw.json", case / "sortformer.json"], check=True)
    if case.name not in ("onboarding", "english-committee", "english-tabletop"):
        return
    for name, options in (("community", []), ("community-count", ["num=3" if case.name == "english-committee" else "num=4"])):
        timed(case, name, [DIAR / ".build/release/diarexp", wav, case / f"{name}.json", *options])
    for variant in ("dihard3", "ami", "callhome", "dihard2"):
        name = f"lseend-{variant}"
        raw = case / f"{name}.raw.json"
        timed(case, name, [fluid, "lseend", wav, "--variant", variant, "--output", raw])
        subprocess.run([*convert, raw, case / f"{name}.json"], check=True)


def recaps(source, case, lang):
    command = [PIPE / ".venv/bin/python", PIPE / "recap.py"]
    timed(case, "pipeline", [*command, "run", source / "call.wav", case / "pipeline", "--language", lang])
    if case.name == "silence":
        return
    exact = case / "exact"
    exact.mkdir()
    turns = [{"speaker_id": t["speaker"], "start_seconds": t["start"], "end_seconds": t["end"], "text": t["text"]}
             for t in load(source / "transcript.json")["segments"]]
    save(exact / "turns.json", turns)
    save(exact / "speakers.json", {"labels": {t["speaker_id"]: "Speaker " + t["speaker_id"] for t in turns}})
    timed(case, "exact", [*command, "summarize", exact])
    timed(case, "fast", [*command, "run", source / "call.wav", case / "fast",
                         "--language", lang, "--asr", "turbo-q4", "--diarizer", "who"])


def run(fixtures, root, phase, cases=None):
    if any((p / ".git").exists() for p in [root, *root.parents]):
        raise ValueError("results must be outside Git")
    build(fixtures, check_only=True)
    verified = weights() if phase == "diarize" else None
    for name in cases or (*SCRIPTS, *CONTROLS):
        source, case = fixtures / name, root / name
        if digest(source / "call.wav") != (case / "input.sha256").read_text().strip():
            raise ValueError(f"wrong input for {name}")
        lang = load(source / "manifest.json").get("language", "zh")
        if phase == "diarize":
            diarize(case, verified)
        elif phase == "split":
            split(source, case, lang)
        elif phase == "recaps" and name in ("onboarding", "english-audit", "silence"):
            recaps(source, case, lang)
        elif phase == "turns" and name != "silence":
            with (case / "turn-order.json").open("x") as report:
                subprocess.run([sys.executable, HERE / "expanded_turn_order.py", source, case, case / "review"],
                               stdout=report, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("phase", choices=("diarize", "recaps", "split", "turns"))
    parser.add_argument("--case", choices=(*SCRIPTS, *CONTROLS), action="append",
                        help="run only this case (repeatable); existing results are never replaced")
    args = parser.parse_args()
    run(args.fixtures.resolve(), args.results.resolve(), args.phase, args.case)
