"""Re-voice the existing collection scripts with Audio8-TTS-Realistic-0.6B, for comparison with the old voices.

Usage: uv run generate_audio8.py OUT [name ...] [--seed 7] [--simplified]
Writes OUT/<name>/ for each named collection script (all fourteen by default), in the same
layout as generate.py. The scripts, turn order, gaps, levelling and mixing stay the same;
only the voices change. Audio8 has a single default voice and clones any other voice from a
reference clip and its transcript, so each old voice is cloned from a fixed sentence spoken
by that voice's own engine (the F5 voice from its pinned reference clip). The references are
kept in OUT/references/. With --simplified, Mandarin turns are converted from Traditional to
Simplified characters with OpenCC t2s before speaking, as the F5 voice's frontend does; the
timed references keep the script's text. These recordings are for comparing voices only; they are not part
of the hashed collection.
"""
import argparse
import json
from pathlib import Path
import time

from collection import SCRIPTS
from emoti_voice import VOICE_IDS as EMOTI_VOICES, render_turns
from f5_voice import VOICE_ID as F5_VOICE, provenance as f5_provenance, reference_path
from generate import LANGUAGES, MODEL as QWEN, RATE, assemble, level

HERE = Path(__file__).resolve().parent
PIN_PATH = HERE / "reference" / "audio8-voice.json"


def provenance():
    """Read the Audio8 pins without loading the model."""
    return json.loads(PIN_PATH.read_text(encoding="utf-8"))


def references_needed(names):
    """List the (voice, language) pairs that the named scripts use."""
    needed = set()
    for name in names:
        script = json.loads(SCRIPTS[name].read_text())
        language = script.get("language", "zh")
        needed |= {(speaker["voice"], language) for speaker in script["speakers"].values()}
    return sorted(needed)


def render_references(folder, needed, pin):
    """Speak the reference sentence once per voice and language with that voice's own engine.

    Returns {(voice, language): (wav path, transcript)}. Clips stay at their engine's native
    rate; Audio8 resamples references to 44.1 kHz itself.
    """
    import numpy as np
    import soundfile as sf

    folder.mkdir(parents=True, exist_ok=True)
    references, missing = {}, []
    for voice, language in needed:
        if voice == F5_VOICE:
            f5 = f5_provenance()["reference"]
            references[voice, language] = (reference_path(f5), f5["text"])
            continue
        path = folder / f"{voice}-{language}.wav"
        references[voice, language] = (path, pin["reference_text"][language])
        if not path.exists():
            missing.append((voice, language))
    seed = pin["reference_seed"]
    emoti = [(voice, language) for voice, language in missing if voice in EMOTI_VOICES]
    if emoti:
        turns = [{"speaker": str(i), "text": pin["reference_text"][language]}
                 for i, (voice, language) in enumerate(emoti)]
        speakers = {str(i): {"voice": voice} for i, (voice, _) in enumerate(emoti)}
        with render_turns(turns, speakers, seed) as clips:
            for i, (voice, language) in enumerate(emoti):
                audio, rate = sf.read(clips[i], dtype="float32")
                sf.write(folder / f"{voice}-{language}.wav", audio, rate, subtype="FLOAT")
    qwen_needed = [(voice, language) for voice, language in missing if voice not in EMOTI_VOICES]
    if qwen_needed:
        import mlx.core as mx
        from mlx_audio.tts.utils import load_model

        qwen = load_model(QWEN[0], revision=QWEN[1])
        for voice, language in qwen_needed:
            mx.random.seed(seed)
            audio = np.concatenate([np.array(result.audio, dtype=np.float32) for result in qwen.generate(
                text=pin["reference_text"][language], voice=voice, lang_code=LANGUAGES[language])])
            sf.write(folder / f"{voice}-{language}.wav", audio, qwen.sample_rate, subtype="FLOAT")
        del qwen
        mx.clear_cache()
    for voice, language in missing:
        print(f"reference {voice} ({language}) written", flush=True)
    return references


def generate(model, script_path, out, references, pin, seed=7, simplified=False):
    import mlx.core as mx
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    script = json.loads(script_path.read_text())
    speakers, turns = script["speakers"], script["turns"]
    language = script.get("language", "zh")
    speak = lambda text: text
    if simplified and language == "zh":
        from opencc import OpenCC

        speak = OpenCC("t2s").convert
    settings = {key: pin["settings"][key] for key in ("temperature", "top_p", "top_k", "max_tokens")}
    (out / "turns").mkdir(parents=True, exist_ok=True)
    mx.reset_peak_memory()
    started = time.time()
    clips, report = [], []
    for i, turn in enumerate(turns):
        voice = speakers[turn["speaker"]]["voice"]
        reference, reference_text = references[voice, language]
        turn_started = time.time()
        results = list(model.generate(text=speak(turn["text"]), ref_audio=str(reference),
                                      ref_text=reference_text, seed=seed + i, **settings))
        if len(results) != 1:
            raise ValueError(f"turn {i + 1}: expected one result, got {len(results)}")
        result = results[0]
        if result.sample_rate != pin["settings"]["sample_rate"]:
            raise ValueError(f"expected {pin['settings']['sample_rate']} Hz speech, got {result.sample_rate}")
        audio = np.array(result.audio, dtype=np.float32).reshape(-1)
        clips.append(level(resample_poly(audio, RATE, result.sample_rate).astype(np.float32)))
        sf.write(out / "turns" / f"{i + 1:02d}-{turn['speaker']}.wav", clips[-1], RATE)
        capped = result.token_count >= settings["max_tokens"]
        report.append({"index": i, "voice": voice, "seconds": round(audio.size / result.sample_rate, 3),
                       "frames": result.token_count, "hit_token_limit": capped,
                       "elapsed_seconds": round(time.time() - turn_started, 2)})
        print(f"{i + 1}/{len(turns)} {turn['speaker']} {voice} {audio.size / result.sample_rate:.1f}s"
              + (" (hit the token limit)" if capped else ""), flush=True)
    elapsed = time.time() - started
    peak = round(mx.get_peak_memory() / 1e9, 2)
    (out / "audio8-report.json").write_text(json.dumps({"turns": report, "peak_memory_gb": peak}, indent=1))
    capped = [t["index"] + 1 for t in report if t["hit_token_limit"]]
    if capped:
        print(f"warning: turns {capped} hit the token limit before ending", flush=True)
    assemble(out, turns, clips, {
        "script": script_path.name, "engine": "audio8",
        "model": {pin["model"]["repository"]: pin["model"]["revision"]},
        "voice_config": {"audio8": pin}, "language": language, "seed": seed, "speakers": speakers,
        "text_form": "simplified (OpenCC t2s)" if simplified and language == "zh" else "as scripted",
        "audio8_references": {f"{voice}/{lang}": {"clip": Path(path).name, "text": text}
                              for (voice, lang), (path, text) in references.items() if lang == language},
        "peak_memory_gb": peak}, elapsed)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("names", nargs="*", choices=[[], *SCRIPTS], metavar="name",
                        help=f"collection scripts to voice (default: all): {', '.join(SCRIPTS)}")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--simplified", action="store_true",
                        help="speak Mandarin turns in Simplified characters, as the F5 voice does")
    args = parser.parse_args()
    names = [name for name in (args.names or SCRIPTS)
             if not (args.out / name / "manifest.json").exists()
             or print(f"{name}: already generated, skipping", flush=True)]
    if not names:
        return
    pin = provenance()
    references = render_references(args.out / "references", references_needed(names), pin)
    from mlx_audio.tts.utils import load_model

    model = load_model(pin["model"]["repository"], revision=pin["model"]["revision"])
    for name in names:
        print(f"{name}: voicing {SCRIPTS[name].name} with Audio8", flush=True)
        generate(model, SCRIPTS[name], args.out / name, references, pin, args.seed, args.simplified)


if __name__ == "__main__":
    main()
