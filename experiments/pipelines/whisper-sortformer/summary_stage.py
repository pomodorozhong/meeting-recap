"""Summary stage: Qwen3.5 9B through mlx-lm. One prompt per transcript chunk, then one merge prompt if needed.

Reads the named transcript lines (JSON list) and writes every prompt's reply with timings; the final
reply holds the notes. Runs in its own process so the model's memory is released when it ends.
"""
import json
import sys
import time

from pins import SUMMARY_REPO, SUMMARY_REVISION, mlx_peak_bytes, snapshot
import pipeline

MAX_TOKENS = 4096


def main(lines_path, out):
    from mlx_lm import generate, load

    with open(lines_path, encoding="utf-8") as handle:
        lines = json.load(handle)
    model, tokenizer = load(snapshot(SUMMARY_REPO, SUMMARY_REVISION))
    replies = []

    def ask(kind, prompt):
        text = tokenizer.apply_chat_template([{"role": "user", "content": prompt}], add_generation_prompt=True,
                                             enable_thinking=False, tokenize=False)
        started = time.time()
        reply = generate(model, tokenizer, prompt=text, max_tokens=MAX_TOKENS)  # greedy decoding
        replies.append({"kind": kind, "prompt_tokens": len(tokenizer.encode(text)),
                        "seconds": time.time() - started, "reply": reply})
        return reply

    parts = pipeline.chunks(lines)
    notes = [pipeline.parse_notes(ask("extract", pipeline.extract_prompt(part, i + 1, len(parts))))
             for i, part in enumerate(parts)]
    if len(parts) > 1:
        ask("merge", pipeline.merge_prompt(notes))
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"model": SUMMARY_REPO, "model_revision": SUMMARY_REVISION, "max_tokens": MAX_TOKENS,
                   "decoding": "greedy", "thinking": False, "chunk_characters": pipeline.CHUNK_CHARACTERS,
                   "chunks": len(parts), "mlx_peak_bytes": mlx_peak_bytes(), "replies": replies},
                  handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:3])
