"""Stage A entry point: one fixed labeled transcript in, one recap per variant out.

Plan: docs/experiments/2026-11-04-recap-stage-real-calls.md. Every variant reads the same transcript file, so
any difference between recaps comes from the recap step alone. Variants change one thing from the baseline A0.
A4 (other recap models) and A5 (the combined winners) are added to the plan's table first, then here.

    uv run --project experiments/recap-stage experiments/recap-stage/run.py TRANSCRIPT.json OUT [--variants A0,A1]

TRANSCRIPT.json is a JSON list of lines like "[00:01:05] Speaker A: ...", as the pipeline's transcript_lines()
writes them. The script runs everything up to the grading, which only a person can do. Each variant writes
OUT/<variant>/{notes.json,summary.md,run.json}, and OUT/inputs.json records the transcript's SHA-256. A variant
whose run.json already exists is skipped; --force reruns it. One process loads the model once and runs the
variants one after another, so only one model is in memory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time

# Pinned recap model, the same as the pipeline's (experiments/pipelines/whisper-sortformer/pins.py).
MODEL_REPO = "mlx-community/Qwen3.5-9B-4bit"
MODEL_REVISION = "8b2b98c00a6b4d291155e4890773ca8f769aee53"
CHUNK_CHARACTERS = 6000  # the pipeline's chunk size
MAX_TOKENS = 4096
THINKING_MAX_TOKENS = 16384  # thinking spends tokens before the JSON, so A2 gets more room
MAX_PROMPT_TOKENS = 32000  # A1 reports "not run" above this, as the plan says, rather than shortening
SECTIONS = ("topics", "decisions", "action_items", "proposals", "open_questions")

# Copied from the pipeline's prompts so this folder stands alone; tests/experiments/test_recap_stage.py
# checks that A0 still matches the pipeline.
SCHEMA = """{
  "topics": [{"title": "...", "summary": "...", "evidence": ["HH:MM:SS"]}],
  "decisions": [{"text": "...", "evidence": ["HH:MM:SS"]}],
  "action_items": [{"task": "...", "owner": null, "due": null, "evidence": ["HH:MM:SS"]}],
  "proposals": [{"text": "...", "evidence": ["HH:MM:SS"]}],
  "open_questions": [{"text": "...", "evidence": ["HH:MM:SS"]}]
}"""

# A0-noise: the same schema with its keys in the opposite order. It should not change what the notes say.
SCHEMA_REORDERED = """{
  "open_questions": [{"text": "...", "evidence": ["HH:MM:SS"]}],
  "proposals": [{"text": "...", "evidence": ["HH:MM:SS"]}],
  "action_items": [{"task": "...", "owner": null, "due": null, "evidence": ["HH:MM:SS"]}],
  "decisions": [{"text": "...", "evidence": ["HH:MM:SS"]}],
  "topics": [{"title": "...", "summary": "...", "evidence": ["HH:MM:SS"]}]
}"""

RULES = """規則：
- 只根據逐字稿內容，不要推測。全部使用繁體中文，英文術語保留原文。
- decisions 只收錄會議中明確同意或拍板的事項；只是提議、建議或尚未定案的放 proposals；沒有答案的問題放 open_questions。
- action_items 的 owner 只有在逐字稿明確指出負責人時才填寫說話者名稱（使用逐字稿中的說話者標籤），否則為 null；due 只有明確提到期限時才填寫原文，否則為 null。
- 每個項目的 evidence 列出支持它的逐字稿行首時間戳（HH:MM:SS），必須是逐字稿中實際出現的時間戳。
- topics 最多 8 個，每個 summary 一到兩句。
- 只輸出一個 JSON 物件，格式如下，不要輸出其他文字："""

# A3: owner only when clear (otherwise "unknown"), a later value replaces an earlier one, the output language stated.
RULES_A3 = """規則：
- 只根據逐字稿內容，不要推測。輸出語言：全部使用繁體中文（即使逐字稿夾雜簡體字或其他語言），英文術語保留原文。
- decisions 只收錄會議中明確同意或拍板的事項；只是提議、建議或尚未定案的放 proposals；沒有答案的問題放 open_questions。
- 同一件事若先後出現不同的數字、日期、人選或結論，以最後一次明確說定的為準，只寫最後的版本；被推翻的舊版本不要列為決議。
- action_items 的 owner：只有逐字稿明確指派或本人明確承諾時，才填寫說話者標籤；不確定是誰時填 "unknown"，不要猜。due 只有明確提到期限時才填寫原文，否則填 "unknown"。
- 每個項目的 evidence 列出支持它的逐字稿行首時間戳（HH:MM:SS），必須是逐字稿中實際出現的時間戳。
- topics 最多 8 個，每個 summary 一到兩句。
- 只輸出一個 JSON 物件，格式如下，不要輸出其他文字："""
SCHEMA_A3 = SCHEMA.replace('"owner": null, "due": null', '"owner": "unknown", "due": "unknown"')


def extract_prompt(lines, part, parts, rules=RULES, schema=SCHEMA):
    where = f"這是會議逐字稿的第 {part}/{parts} 段。" if parts > 1 else "這是一場會議的逐字稿。"
    return (f"{where}請整理出主題、決議、待辦事項、提議與未解決問題。\n\n{rules}\n{schema}\n\n"
            "逐字稿：\n" + "\n".join(lines))


def merge_prompt(notes, rules=RULES, schema=SCHEMA):
    return ("以下是同一場會議各段逐字稿整理出的 JSON 筆記，依時間順序排列。請合併成一份：合併重複項目並保留所有 evidence 時間戳，"
            "不要新增筆記中沒有的內容。\n\n" + rules + "\n" + schema + "\n\n筆記：\n"
            + "\n".join(json.dumps(n, ensure_ascii=False) for n in notes))


# name -> what changes from A0. chunked=False sends the whole transcript in one prompt.
VARIANTS = {
    "A0": {"change": "none: today's recap", "chunked": True, "thinking": False, "rules": RULES, "schema": SCHEMA},
    "A0-noise": {"change": "JSON keys of the schema reordered", "chunked": True, "thinking": False,
                 "rules": RULES, "schema": SCHEMA_REORDERED},
    "A1": {"change": "whole transcript in one pass", "chunked": False, "thinking": False,
           "rules": RULES, "schema": SCHEMA},
    "A2": {"change": "thinking on", "chunked": True, "thinking": True, "rules": RULES, "schema": SCHEMA},
    "A3": {"change": "rewritten prompt", "chunked": True, "thinking": False, "rules": RULES_A3,
           "schema": SCHEMA_A3},
}


def chunks(lines, size=CHUNK_CHARACTERS):
    """Split transcript lines into chunks of about `size` characters, never splitting a line."""
    output, current, length = [], [], 0
    for line in lines:
        if current and length + len(line) > size:
            output.append(current)
            current, length = [], 0
        current.append(line)
        length += len(line) + 1
    if current:
        output.append(current)
    return output


def parse_notes(text):
    """Read the model's JSON object, tolerating thinking text, a code fence or text around it."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    if "</think>" in text:  # the template already opened the thinking block
        text = text.rsplit("</think>", 1)[1]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("summary model returned no JSON object")
    notes = json.loads(text[start:end + 1])
    if not isinstance(notes, dict):
        raise ValueError("summary model returned JSON that is not an object")
    return {key: [item for item in notes.get(key) or [] if isinstance(item, dict)] for key in SECTIONS}


def check_evidence(notes, lines):
    """Keep only evidence timestamps that start a transcript line; count what was dropped or left unsupported."""
    known = {line[1:9] for line in lines}
    dropped, unsupported = 0, 0
    for key in SECTIONS:
        for item in notes[key]:
            given = [str(e).strip("[] ") for e in item.get("evidence") or []]
            kept = [e for e in given if e in known]
            dropped += len(given) - len(kept)
            item["evidence"] = sorted(set(kept))
            unsupported += not kept
    return {"evidence_dropped": dropped, "items_without_evidence": unsupported}


def summary_markdown(notes, title):
    def cite(item):
        evidence = item.get("evidence") or []
        return f" ({', '.join(evidence)})" if evidence else " (no supporting timestamp)"

    def text(item, key="text"):
        return str(item.get(key) or "").strip()

    lines = [f"# {title}", ""]
    lines += ["## Topics", ""]
    lines += [f"- **{text(t, 'title')}**: {text(t, 'summary')}{cite(t)}" for t in notes["topics"]] or ["- None"]
    lines += ["", "## Decisions", ""]
    lines += [f"- {text(d)}{cite(d)}" for d in notes["decisions"]] or ["- None stated"]
    lines += ["", "## Action items", ""]
    lines += [f"- {text(a, 'task')} — owner: {text(a, 'owner') or 'unknown'}; due: {text(a, 'due') or 'unknown'}{cite(a)}"
              for a in notes["action_items"]] or ["- None stated"]
    lines += ["", "## Proposals (not decided)", ""]
    lines += [f"- {text(p)}{cite(p)}" for p in notes["proposals"]] or ["- None"]
    lines += ["", "## Open questions", ""]
    lines += [f"- {text(q)}{cite(q)}" for q in notes["open_questions"]] or ["- None"]
    return "\n".join(lines) + "\n"


class Model:
    """The pinned recap model through mlx-lm. Tests replace this class with a fake."""

    def __init__(self):
        from huggingface_hub import snapshot_download
        from mlx_lm import load

        path = snapshot_download(repo_id=MODEL_REPO, revision=MODEL_REVISION)
        if Path(path).name != MODEL_REVISION:
            raise ValueError(f"{MODEL_REPO} snapshot {Path(path).name} does not match the pinned {MODEL_REVISION}")
        self.model, self.tokenizer = load(path)

    def render(self, prompt, thinking):
        return self.tokenizer.apply_chat_template([{"role": "user", "content": prompt}], add_generation_prompt=True,
                                                  enable_thinking=thinking, tokenize=False)

    def count(self, text):
        return len(self.tokenizer.encode(text))

    def generate(self, text, max_tokens):
        from mlx_lm import generate

        return generate(self.model, self.tokenizer, prompt=text, max_tokens=max_tokens)  # greedy decoding

    def reset_peak(self):
        import mlx.core as mx

        (getattr(mx, "reset_peak_memory", None) or mx.metal.reset_peak_memory)()

    def peak_bytes(self):
        import mlx.core as mx

        return int((getattr(mx, "get_peak_memory", None) or mx.metal.get_peak_memory)())


def run_variant(name, lines, model, max_prompt_tokens=MAX_PROMPT_TOKENS):
    """Run one variant. Returns (run record, notes or None); notes is None when it was not run or failed."""
    spec = VARIANTS[name]
    max_tokens = THINKING_MAX_TOKENS if spec["thinking"] else MAX_TOKENS
    record = {"variant": name, "change": spec["change"], "model": MODEL_REPO, "model_revision": MODEL_REVISION,
              "decoding": "greedy", "thinking": spec["thinking"], "max_tokens": max_tokens,
              "chunk_characters": CHUNK_CHARACTERS if spec["chunked"] else None}
    parts = chunks(lines) if spec["chunked"] else [lines]
    record["chunks"] = len(parts)
    prompts = [extract_prompt(part, i + 1, len(parts), spec["rules"], spec["schema"]) for i, part in enumerate(parts)]
    rendered = [model.render(p, spec["thinking"]) for p in prompts]
    longest = max(model.count(t) for t in rendered)
    record["longest_prompt_tokens"] = longest
    if longest > max_prompt_tokens:
        record.update(status="not run", reason=f"prompt of {longest} tokens is over the {max_prompt_tokens} limit")
        return record, None
    model.reset_peak()
    replies, started = [], time.time()

    def ask(kind, text):
        begun = time.time()
        reply = model.generate(text, max_tokens)
        replies.append({"kind": kind, "prompt_tokens": model.count(text), "seconds": time.time() - begun,
                        "reply": reply})
        return reply

    try:
        notes = [parse_notes(ask("extract", text)) for text in rendered]
        if len(notes) > 1:
            notes = [parse_notes(ask("merge", model.render(merge_prompt(notes, spec["rules"], spec["schema"]),
                                                           spec["thinking"])))]
        final = notes[0]
        record.update(status="done", evidence=check_evidence(final, lines))
    except ValueError as error:  # unparsable JSON is a result to report, not a crash
        record.update(status="failed", reason=str(error))
        final = None
    record.update(seconds=time.time() - started, mlx_peak_bytes=model.peak_bytes(), replies=replies)
    return record, final


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("transcript", type=Path, help="JSON list of labeled transcript lines")
    parser.add_argument("out", type=Path)
    parser.add_argument("--variants", default="A0,A0-noise,A1,A2,A3",
                        help="comma-separated; any of " + ", ".join(VARIANTS))
    parser.add_argument("--force", action="store_true", help="rerun variants that already have a run.json")
    parser.add_argument("--max-prompt-tokens", type=int, default=MAX_PROMPT_TOKENS)
    args = parser.parse_args(argv)
    names = [n for n in args.variants.split(",") if n]
    unknown = [n for n in names if n not in VARIANTS]
    if unknown:
        parser.error(f"unknown variant {', '.join(unknown)}; choose from {', '.join(VARIANTS)}")

    raw = args.transcript.read_bytes()
    lines = json.loads(raw)
    if not isinstance(lines, list) or not lines or not all(isinstance(x, str) for x in lines):
        parser.error("the transcript must be a non-empty JSON list of strings")
    if not all(re.match(r"\[\d\d:\d\d:\d\d\] ", x) for x in lines):
        parser.error('every transcript line must start with a timestamp like "[00:01:05] "')
    args.out.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(raw).hexdigest()
    inputs = args.out / "inputs.json"
    if inputs.exists() and json.loads(inputs.read_text())["transcript_sha256"] != digest:
        parser.error(f"{args.out} holds recaps of a different transcript; use a new folder")
    inputs.write_text(json.dumps({"transcript_sha256": digest, "lines": len(lines)}, indent=1) + "\n")

    todo = [n for n in names if args.force or not (args.out / n / "run.json").exists()]
    model = Model() if todo else None
    for name in names:
        if name not in todo:
            print(f"{name}: already done, skipping (--force reruns it)")
            continue
        record, notes = run_variant(name, lines, model, args.max_prompt_tokens)
        folder = args.out / name
        folder.mkdir(exist_ok=True)
        if notes is not None:
            (folder / "notes.json").write_text(json.dumps(notes, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            (folder / "summary.md").write_text(summary_markdown(notes, f"Recap {name}"), encoding="utf-8")
        # run.json is written last, so its presence means the variant finished (done, failed or not run).
        (folder / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{name}: {record['status']}" + (f" ({record['reason']})" if "reason" in record else ""))


if __name__ == "__main__":
    sys.exit(main())
