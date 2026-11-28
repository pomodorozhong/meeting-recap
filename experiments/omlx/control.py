"""The stage's recap, run the way summary_stage.py runs it, but with oMLX's pinned MLX and mlx-lm.

    uv run --project experiments/omlx experiments/omlx/control.py LINES.json OUT.json

If this matches oMLX's reply but not the stage's, the newer MLX and mlx-lm cause the difference, not the server.
"""
import json
from pathlib import Path
import sys
import time

from common import MAX_TOKENS, extract_prompt, read_lines

MODEL_REPO = "mlx-community/Qwen3.5-9B-4bit"
MODEL_REVISION = "8b2b98c00a6b4d291155e4890773ca8f769aee53"


def snapshot():
    from huggingface_hub import snapshot_download

    path = snapshot_download(repo_id=MODEL_REPO, revision=MODEL_REVISION)
    if Path(path).name != MODEL_REVISION:
        raise ValueError(f"{MODEL_REPO} snapshot {Path(path).name} does not match the pinned {MODEL_REVISION}")
    return path


def main(lines_path, out):
    import mlx.core as mx
    from mlx_lm import generate, load

    lines = read_lines(lines_path)
    model, tokenizer = load(snapshot())
    text = tokenizer.apply_chat_template([{"role": "user", "content": extract_prompt(lines)}],
                                         add_generation_prompt=True, enable_thinking=False, tokenize=False)
    started = time.time()
    reply = generate(model, tokenizer, prompt=text, max_tokens=MAX_TOKENS)  # greedy decoding
    record = {"runner": "control", "model": MODEL_REPO, "model_revision": MODEL_REVISION,
              "replies": [{"kind": "extract", "prompt_tokens": len(tokenizer.encode(text)),
                           "seconds": time.time() - started, "reply": reply}],
              "mlx_peak_bytes": int(mx.get_peak_memory())}
    Path(out).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:3])
