"""Summary stage: Qwen3.5 9B through mlx-lm. One prompt per transcript chunk, then one merge prompt if needed.

Reads the named transcript lines (JSON list) and writes every prompt's reply with timings; the final
reply holds the notes. Runs in its own process so the model's memory is released when it ends.
"""
import argparse
import json
import time

from pins import SUMMARY_REPO, SUMMARY_REVISION, mlx_peak_bytes, snapshot
import pipeline

MAX_TOKENS = 4096


ACTION_PROMPT = """從逐字稿抽取會議結束時仍然成立的待辦。逐項確認：具體要交付什麼、最後誰負責、最後期限。
分開處理不同工作。後面的更正、接受交接或取消優先。不要把提議、未觸發的條件、已完成或被否決的工作列為待辦。
負責人使用逐字稿的 Speaker 標籤；負責人或期限未定就填 null。保留交付對象、範圍、期限限定，不要猜。
每項 evidence 引用足以證明工作、最終負責人和期限的全部必要行首時間戳。若答案分散在多行，要一併引用。
沒有待辦時輸出空陣列。只輸出 JSON：{"action_items":[{"task":"...","owner":null,"due":null,"evidence":["HH:MM:SS"]}]}
逐字稿：
"""


def main(lines_path, out, actions_only=False):
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
    if actions_only and len(parts) != 1:
        raise ValueError("the experimental focused prompt requires a single transcript chunk")
    if actions_only:
        ask("actions", ACTION_PROMPT + "\n".join(lines))
    else:
        full_recap(parts, ask)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"model": SUMMARY_REPO, "model_revision": SUMMARY_REVISION, "max_tokens": MAX_TOKENS,
                   "decoding": "greedy", "thinking": False, "chunk_characters": pipeline.CHUNK_CHARACTERS,
                   "chunks": len(parts), "mlx_peak_bytes": mlx_peak_bytes(), "replies": replies}, handle, ensure_ascii=False, indent=1)


def full_recap(parts, ask):
    notes = [pipeline.parse_notes(ask("extract", pipeline.extract_prompt(part, i + 1, len(parts))))
             for i, part in enumerate(parts)]
    if len(parts) > 1:
        ask("merge", pipeline.merge_prompt(notes))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lines_path")
    parser.add_argument("out")
    parser.add_argument("--actions-only", action="store_true", help="experimental single-chunk action extractor")
    args = parser.parse_args()
    main(args.lines_path, args.out, args.actions_only)
