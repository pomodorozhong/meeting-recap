"""Run the pinned Community-1 pipeline and write segments plus model metadata."""
import argparse
import json
from pathlib import Path
import re
import sys
import time

MODEL = "pyannote/speaker-diarization-community-1"
REVISION = "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"


def revision(value):
    if not re.fullmatch(r"[0-9a-fA-F]{40}", value):
        raise argparse.ArgumentTypeError("revision must be a full 40-character commit SHA")
    return value.lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav")
    parser.add_argument("out", type=Path)
    parser.add_argument("num_speakers", type=int, nargs="?")
    parser.add_argument("--revision", type=revision, default=REVISION)
    args = parser.parse_args()
    import torch
    from pyannote.audio import Pipeline

    # Community-1's bundled segmentation, embedding, and PLDA assets inherit this revision.
    pipe = Pipeline.from_pretrained(MODEL, revision=args.revision)
    if pipe is None:
        raise RuntimeError("could not load the pinned pipeline; accept its Hugging Face terms and authenticate")
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    pipe.to(torch.device(device))
    started = time.time()
    options = {"num_speakers": args.num_speakers} if args.num_speakers is not None else {}
    result = pipe(args.wav, **options)
    elapsed = time.time() - started
    annotation = getattr(result, "exclusive_speaker_diarization", None) or getattr(result, "speaker_diarization", result)
    segments = [{"speaker_id": speaker, "start_seconds": turn.start, "end_seconds": turn.end}
                for turn, _, speaker in annotation.itertracks(yield_label=True)]
    with args.out.open("w", encoding="utf-8") as handle:
        json.dump(segments, handle, indent=1)
    metadata = {"model": MODEL, "model_revision": args.revision, "device": device, "elapsed_seconds": elapsed,
                "config": options}
    with args.out.with_suffix(".metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=1)
    print(json.dumps(metadata))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError) as error:
        sys.exit(str(error))
