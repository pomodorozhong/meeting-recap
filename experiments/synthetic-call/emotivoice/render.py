"""Render selected EmotiVoice turns in the isolated, locked CPU environment."""
import hashlib
import json
import os
from pathlib import Path
import sys

from assets import prepare_assets, provenance


def load_request(path):
    request = json.loads(path.read_text(encoding="utf-8"))
    seed = request["seed"]
    if (not isinstance(seed, int) or isinstance(seed, bool)
            or not 0 <= seed < 2 ** 32):
        raise ValueError("seed must be an integer from 0 through 2**32 - 1")
    voices = provenance()["voices"]
    seen = set()
    for turn in request["turns"]:
        index = turn["index"]
        if not isinstance(index, int) or isinstance(index, bool) or index < 0 or index in seen:
            raise ValueError("turn indices must be unique nonnegative integers")
        seen.add(index)
        if turn["voice"] not in voices:
            raise ValueError(f"unsupported EmotiVoice preset: {turn['voice']}")
        if not isinstance(turn["text"], str) or not turn["text"].strip():
            raise ValueError("turn text must be a nonempty string")
    return request


def render(request, output):
    pin = provenance()
    if pin["settings"]["device"] != "cpu" or pin["settings"]["dtype"] != "float32":
        raise ValueError("this EmotiVoice backend requires CPU float32 inference")
    paths = prepare_assets()
    # g2p_en checks these resources during import. Select the verified directory
    # before importing the source frontend, and retain its required ZIP files.
    os.environ["NLTK_DATA"] = str(paths["nltk"])
    import nltk
    nltk.data.path = [str(paths["nltk"])]
    os.chdir(paths["code"])
    sys.path.insert(0, str(paths["code"]))

    import numpy as np
    import soundfile as sf
    import torch
    from transformers import AutoTokenizer
    from yacs import config as config_loader
    from opencc import OpenCC
    from config.joint.config import Config
    from models.prompt_tts_modified.simbert import StyleEncoder
    from models.prompt_tts_modified.jets import JETSGenerator
    from frontend import g2p_cn_en, read_lexicon, G2p

    seed = request["seed"]
    torch.manual_seed(seed)
    torch.set_num_threads(pin["settings"]["num_threads"])
    torch.use_deterministic_algorithms(pin["settings"]["deterministic_algorithms"])
    np.random.seed(seed)
    config = Config()
    if config.sampling_rate != pin["settings"]["sample_rate"]:
        raise ValueError("source sample rate differs from the pinned setting")
    config.bert_path = str(paths["encoder"])
    with open(config.model_config_path) as handle:
        model_config = config_loader.load_cfg(handle)
    model_config.n_vocab = config.n_symbols
    model_config.n_speaker = config.speaker_n_labels
    style = StyleEncoder(config).eval()
    state = torch.load(paths["tts"] / "checkpoint_163431", map_location="cpu", weights_only=True)["model"]
    style.load_state_dict({name[7:]: value for name, value in state.items()}, strict=False)
    del state
    generator = JETSGenerator(model_config).eval()
    state = torch.load(paths["tts"] / "g_00140000", map_location="cpu", weights_only=True)
    generator.load_state_dict(state["generator"])
    del state
    tokenizer = AutoTokenizer.from_pretrained(config.bert_path, local_files_only=True)
    lexicon = read_lexicon(str(paths["code"] / "lexicon/librispeech-lexicon.txt"))
    g2p = G2p()
    simplify = OpenCC("t2s")
    tokens = {token: index for index, token in enumerate(config.tokens)}
    speakers = {speaker: index for index, speaker in enumerate(config.speakers)}

    def embed(text):
        return style(**tokenizer([text], return_tensors="pt"))["pooled_output"]

    output.mkdir(parents=True, exist_ok=False)
    results = []
    with torch.inference_mode():
        style_embedding = embed(pin["settings"]["style_prompt"])
        prepared = []
        for turn in request["turns"]:
            text = simplify.convert(turn["text"])
            phonemes = g2p_cn_en(text, g2p, lexicon).split()
            prepared.append((torch.LongTensor([[tokens[value] for value in phonemes]]), embed(text)))
        for turn, (sequence, content) in zip(request["turns"], prepared, strict=True):
            speaker = pin["voices"][turn["voice"]]["speaker_id"]
            torch.manual_seed(seed)
            audio = generator(
                inputs_ling=sequence, inputs_style_embedding=style_embedding,
                input_lengths=torch.LongTensor([sequence.shape[1]]),
                inputs_content_embedding=content,
                inputs_speaker=torch.LongTensor([speakers[speaker]]),
                alpha=pin["settings"]["alpha"],
            )["wav_predictions"].squeeze().numpy()
            rate = config.sampling_rate
            if (not np.isfinite(audio).all() or not rate * 0.5 < len(audio) < rate * 30
                    or float(np.max(np.abs(audio))) <= 0.002):
                raise ValueError(f"unusable EmotiVoice audio for turn {turn['index']}")
            name = f"{turn['index']:03d}.wav"
            sf.write(output / name, audio, rate, subtype="FLOAT")
            results.append({"index": turn["index"], "voice": turn["voice"], "file": name,
                            "sample_rate": rate,
                            "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest()})
            print(f"EmotiVoice {speaker}: turn {turn['index']}", flush=True)
    (output / "manifest.json").write_text(
        json.dumps({"seed": seed, "turns": results}, indent=2) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: render.py REQUEST.json OUT_DIR")
    request_path = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    render(load_request(request_path), output)


if __name__ == "__main__":
    main()
