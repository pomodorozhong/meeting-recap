"""Write OUT/<call>/lines.json, the exact-turn transcript lines every runner reads.

    uv run --project experiments/omlx experiments/omlx/lines.py FIXTURES OUT
"""
import json
from pathlib import Path
import sys

from common import CALLS, chunks, exact_lines


def main(fixtures, out, convert=None):
    if convert is None:
        from opencc import OpenCC

        convert = OpenCC("s2tw").convert
    for call in CALLS:
        lines = exact_lines(json.loads((Path(fixtures) / call / "transcript.json").read_text()), convert)
        if len(chunks(lines)) != 1:
            sys.exit(f"{call} needs more than one chunk; this check covers one-prompt recaps only")
        folder = Path(out) / call
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "lines.json").write_text(json.dumps(lines, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{call}: {len(lines)} lines")


if __name__ == "__main__":
    main(*sys.argv[1:3])
