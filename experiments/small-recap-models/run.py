"""Recaps of the synthetic collection's exact turns from one recap model.

Plan: docs/experiments/2026-11-28-small-recap-models.md. Every model gets the same transcript lines and the same
prompt as the pipeline's recap with Qwen3.5 9B, so any difference between recaps comes from the model alone.

    uv run --project experiments/small-recap-models experiments/small-recap-models/run.py FIXTURES OUT --model NAME

FIXTURES is the verified 17-recording collection. For each case, the script turns the script's exact turns into
transcript lines the way the pipeline's `summarize` does for the `exact` arm of the collection run, and writes
OUT/<case>/lines.json. Each model then writes OUT/<case>/<run>/{notes.json,summary.md,run.json}, where <run> is
the model name, or the name plus "-thinking" with --thinking, "-thinking-budget" with --thinking-budget or
"-thinking-sampled" with --thinking-sampled. A run whose run.json already exists for a case is
skipped; --force reruns it, and --todo prints the cases that would run. run.sh runs each model in its own process, so
only one model is in memory at a time.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time

CASES = ("onboarding", "english-audit")

# name -> (Hugging Face repo, pinned revision, loader). LFM3 has no mlx-lm support yet, so it loads through
# mlx-vlm, the route its official MLX build documents. Both run on MLX, as decision 7 requires.
MODELS = {
    "qwen3.5-9b": ("mlx-community/Qwen3.5-9B-4bit", "8b2b98c00a6b4d291155e4890773ca8f769aee53", "mlx-lm"),
    "gemma4-e2b": ("lmstudio-community/gemma-4-E2B-it-MLX-4bit", "31512dab743c73974a99795270031a6f85072d94", "mlx-lm"),
    "minicpm5-2b": ("openbmb/MiniCPM5-2B-MLX", "c8c072dbfbc5ce9c8faf3fbff9665b86fdc29c62", "mlx-lm"),
    "lfm3-1.7b": ("LiquidAI/LFM3-1.7B-MLX-4bit", "91f34088d6946482cbcae11b85d4657093618c34", "mlx-vlm"),
    "spark-x2.6-4b": ("mlx-community/Spark-X2.6-4B-OptiQ-4bit", "6d83e911abefcbbb9c7c595e6517264f36db03dd", "mlx-lm"),
}

# Copied from the pipeline (experiments/pipelines/whisper-sortformer/pipeline.py) so this folder stands alone;
# tests/experiments/test_small_recap_models.py checks that they still match.
CHUNK_CHARACTERS = 6000
MAX_TOKENS = 4096
THINKING_MAX_TOKENS = 16384  # thinking spends tokens before the JSON, as in the recap-stage plan's A2
THINKING_BUDGET = 2048  # the budget arm closes the thinking after this many reply tokens, as oMLX's thinking_budget does
BUDGET_MAX_TOKENS = THINKING_BUDGET + MAX_TOKENS  # the same room for the JSON as with thinking off
SEED = 0  # the sampled arm's one seed, set before each reply

# Thinking-on variants: greedy (the first thinking-on arm), a thinking budget with greedy decoding, or each model
# card's recommended sampling for thinking. Gemma4 E2B finished with greedy thinking, so it has no sampling entry.
VARIANTS = ("greedy", "budget", "sampled")
SAMPLING = {
    # Qwen/Qwen3.5-9B model card at c2022362, "thinking mode for general tasks"
    "qwen3.5-9b": {"temperature": 1.0, "top_p": 0.95, "top_k": 20, "min_p": 0.0, "presence_penalty": 1.5},
    # MiniCPM5-2B-MLX model card and generation_config.json at c8c072db
    "minicpm5-2b": {"temperature": 1.0, "top_p": 0.95, "min_p": 0.0},
    # LFM3-1.7B-MLX-4bit model card's thinking example and generation_config.json at 91f34088
    "lfm3-1.7b": {"temperature": 0.1, "top_k": 50, "repetition_penalty": 1.1},
    # Spark-X2.6-4B-OptiQ-4bit generation_config.json at 6d83e911
    "spark-x2.6-4b": {"temperature": 1.0, "top_p": 0.95},
}
THINK_START, THINK_END = "<think>", "</think>"  # all four models in SAMPLING open and close their thinking with them
MAX_GAP_SECONDS = 1.0
SECTIONS = ("topics", "decisions", "action_items", "proposals", "open_questions")

SCHEMA = """{
  "topics": [{"title": "...", "summary": "...", "evidence": ["HH:MM:SS"]}],
  "decisions": [{"text": "...", "evidence": ["HH:MM:SS"]}],
  "action_items": [{"task": "...", "owner": null, "due": null, "evidence": ["HH:MM:SS"]}],
  "proposals": [{"text": "...", "evidence": ["HH:MM:SS"]}],
  "open_questions": [{"text": "...", "evidence": ["HH:MM:SS"]}]
}"""

RULES = """規則：
- 只根據逐字稿內容，不要推測。全部使用繁體中文，英文術語保留原文。
- decisions 只收錄會議中明確同意或拍板的事項；只是提議、建議或尚未定案的放 proposals；沒有答案的問題放 open_questions。
- action_items 的 owner 只有在逐字稿明確指出負責人時才填寫說話者名稱（使用逐字稿中的說話者標籤），否則為 null；due 只有明確提到期限時才填寫原文，否則為 null。
- 每個項目的 evidence 列出支持它的逐字稿行首時間戳（HH:MM:SS），必須是逐字稿中實際出現的時間戳。
- topics 最多 8 個，每個 summary 一到兩句。
- 只輸出一個 JSON 物件，格式如下，不要輸出其他文字："""


def extract_prompt(lines, part=1, parts=1):
    where = f"這是會議逐字稿的第 {part}/{parts} 段。" if parts > 1 else "這是一場會議的逐字稿。"
    return (f"{where}請整理出主題、決議、待辦事項、提議與未解決問題。\n\n{RULES}\n{SCHEMA}\n\n"
            "逐字稿：\n" + "\n".join(lines))


def merge_prompt(notes):
    return ("以下是同一場會議各段逐字稿整理出的 JSON 筆記，依時間順序排列。請合併成一份：合併重複項目並保留所有 evidence 時間戳，"
            "不要新增筆記中沒有的內容。\n\n" + RULES + "\n" + SCHEMA + "\n\n筆記：\n"
            + "\n".join(json.dumps(n, ensure_ascii=False) for n in notes))


def stamp(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _joins(left, right):
    return not (left[-1:].isascii() and left[-1:].isalnum() and right[:1].isascii() and right[:1].isalnum())


def named_turns(turns, labels, convert=lambda text: text):
    """The pipeline's named_turns for turns without ASR segments: adjacent turns of one speaker join."""
    output = []
    for turn in turns:
        name = labels[turn["speaker_id"]].strip()
        text = convert(turn["text"])
        if output and output[-1]["speaker"] == name and turn["start_seconds"] - output[-1]["end_seconds"] <= MAX_GAP_SECONDS:
            output[-1]["end_seconds"] = max(output[-1]["end_seconds"], turn["end_seconds"])
            output[-1]["text"] += ("" if _joins(output[-1]["text"], text) else " ") + text
        else:
            output.append({"speaker": name, "start_seconds": turn["start_seconds"],
                           "end_seconds": turn["end_seconds"], "text": text})
    return output


def transcript_lines(turns):
    return [f"[{stamp(t['start_seconds'])}] {t['speaker']}: {t['text']}" for t in turns]


def exact_lines(transcript, convert):
    """The collection run's `exact` arm: the script's turns, each speaker labeled "Speaker <id>"."""
    turns = [{"speaker_id": s["speaker"], "start_seconds": s["start"], "end_seconds": s["end"], "text": s["text"]}
             for s in transcript["segments"]]
    labels = {t["speaker_id"]: "Speaker " + t["speaker_id"] for t in turns}
    return transcript_lines(named_turns(turns, labels, convert))


def chunks(lines, size=CHUNK_CHARACTERS):
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
    for close in ("</think>", "<channel|>"):  # Gemma 4 closes its thinking channel with <channel|>
        if close in text:
            text = text.rsplit(close, 1)[1]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("summary model returned no JSON object")
    try:
        notes = json.loads(text[start:end + 1])
    except json.JSONDecodeError as error:
        raise ValueError(f"summary model returned invalid JSON: {error}") from None
    if not isinstance(notes, dict):
        raise ValueError("summary model returned JSON that is not an object")
    return {key: [item for item in notes.get(key) or [] if isinstance(item, dict)] for key in SECTIONS}


THINK_CLOSES = ("</think>", "<channel|>")


def capped_in_thinking(reply, reply_tokens, max_tokens):
    """A thinking reply that reached the cap without closing its thinking: any JSON in it is a draft, not the answer.

    The plan counts it as unreadable. run.py now records the generator's own token count; runs made before that
    counted by encoding the reply again, so a token is allowed for that count's rounding at the cap.
    """
    return reply_tokens >= max_tokens - 1 and not any(close in reply for close in THINK_CLOSES)


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


def summary_markdown(notes, title="Meeting recap"):
    def cite(item):
        evidence = item.get("evidence") or []
        return f" ({', '.join(evidence)})" if evidence else " (no supporting timestamp)"

    def text(item, key="text"):
        return str(item.get(key) or "").strip()

    lines = [f"# {title}", "",
             "Generated by a local model from the transcript. Check each point against the cited timestamps.", ""]
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


class ThinkingBudget:
    """A logits processor that closes the thinking after `budget` reply tokens, as oMLX's ThinkingBudgetProcessor does.

    Both mlx-lm and mlx-vlm call a processor once per reply token with every token so far, the prompt first. Once
    the reply reaches the budget without the close tag, it forces `force` (a newline, the tag and a blank line)
    one token at a time, then does nothing. If the model closes its thinking itself, it never acts.

    It only acts while the thinking is open: from the start when the prompt ends inside an open thinking block
    (`opened`), or else from when the reply writes `open_ids`. A reply that never opens its thinking is left alone,
    so the close tag is never forced into an answer.
    """

    def __init__(self, close_ids, force, budget, open_ids=(), opened=True):
        self.close_ids, self.force, self.budget = list(close_ids), list(force), budget
        self.open_ids, self.opened = list(open_ids), opened
        self.prompt_length, self.reply, self.forced, self.done = None, [], 0, False

    def __call__(self, tokens, logits):
        if self.prompt_length is None:
            self.prompt_length = len(tokens)
        else:
            self.reply.append(int(tokens[-1].item()))
        if self.done:
            return logits
        if not self.opened:
            self.opened = bool(self.open_ids) and self.reply[-len(self.open_ids):] == self.open_ids
            if not self.opened:
                return logits
        if self.forced == 0 and self.reply[-len(self.close_ids):] == self.close_ids:
            self.done = True
            return logits
        if self.forced == 0 and len(self.reply) < self.budget:
            return logits
        if self.forced == len(self.force):
            self.done = True
            return logits
        import mlx.core as mx

        token = self.force[self.forced]
        self.forced += 1
        keep = mx.arange(logits.shape[-1]) == token
        return mx.where(keep, logits, mx.array(-float("inf"), dtype=logits.dtype))


def thinking_open(text):
    """Whether a rendered prompt ends inside an open thinking block, as the thinking-on templates leave it."""
    return text.rfind(THINK_START) > text.rfind(THINK_END)


class ReplyOnly:
    """Runs a penalty processor on the reply tokens only, leaving out the prompt that comes first."""

    def __init__(self, processor):
        self.processor, self.prompt_length = processor, None

    def __call__(self, tokens, logits):
        if self.prompt_length is None:
            self.prompt_length = len(tokens)
        return self.processor(tokens[self.prompt_length:], logits)


class Model:
    """One pinned model through mlx-lm or mlx-vlm, greedy unless sampled, thinking off unless asked. Tests replace it."""

    def __init__(self, name):
        from huggingface_hub import snapshot_download

        self.repo, self.revision, self.loader = MODELS[name]
        path = snapshot_download(repo_id=self.repo, revision=self.revision)
        if Path(path).name != self.revision:
            raise ValueError(f"{self.repo} snapshot {Path(path).name} does not match the pinned {self.revision}")
        if self.loader == "mlx-lm":
            from mlx_lm import load

            self.model, self.tokenizer = load(path)  # never trust_remote_code: repository code is not run
            self.processor = None
        else:
            from mlx_vlm import load

            self.model, self.processor = load(path)
            self.tokenizer = getattr(self.processor, "tokenizer", self.processor)

    def render(self, prompt, thinking=False):
        return self.tokenizer.apply_chat_template([{"role": "user", "content": prompt}], add_generation_prompt=True,
                                                  enable_thinking=thinking, tokenize=False)

    def count(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def budget(self, budget, text):
        encode = lambda piece: self.tokenizer.encode(piece, add_special_tokens=False)
        return ThinkingBudget(encode(THINK_END), encode("\n" + THINK_END + "\n\n"), budget,
                              open_ids=encode(THINK_START), opened=thinking_open(text))

    def generate(self, text, max_tokens=MAX_TOKENS, budget=None, sampling=None):
        """Returns (reply text, number of tokens generated)."""
        import mlx.core as mx
        from mlx_lm.sample_utils import make_presence_penalty

        processors = [self.budget(budget, text)] if budget else []
        sampling = sampling or {}
        mx.random.seed(SEED)
        # The repetition penalty counts the prompt and the reply, as in Transformers, whose settings the cards that
        # use it give. The presence penalty counts only the reply, as in vLLM and the OpenAI API, whose option it is.
        if "presence_penalty" in sampling:
            processors.append(ReplyOnly(make_presence_penalty(sampling["presence_penalty"], max_tokens)))
        repetition = {"repetition_penalty": sampling["repetition_penalty"],
                      "repetition_context_size": max_tokens} if "repetition_penalty" in sampling else {}
        if self.loader == "mlx-lm":
            from mlx_lm import stream_generate
            from mlx_lm.sample_utils import make_logits_processors, make_sampler

            sampler = make_sampler(temp=sampling.get("temperature", 0.0), top_p=sampling.get("top_p", 0.0),
                                   min_p=sampling.get("min_p", 0.0), top_k=sampling.get("top_k", 0))
            processors += make_logits_processors(**repetition) if repetition else []
            reply, generated = "", 0
            for response in stream_generate(self.model, self.tokenizer, prompt=text, max_tokens=max_tokens,
                                            sampler=sampler, logits_processors=processors or None):
                reply += response.text
                generated = response.generation_tokens
            return reply, generated
        from mlx_vlm import generate

        options = {"temperature": sampling.get("temperature", 0.0)}
        options.update({key: sampling[key] for key in ("top_p", "top_k", "min_p") if key in sampling})
        options.update(repetition)
        if processors:
            options["logits_processors"] = processors
        result = generate(self.model, self.processor, text, max_tokens=max_tokens, verbose=False, **options)
        return result.text, result.generation_tokens

    def reset_peak(self):
        import mlx.core as mx

        mx.reset_peak_memory()

    def peak_bytes(self):
        import mlx.core as mx

        return int(mx.get_peak_memory())


def run_id(name, thinking, variant="greedy"):
    if not thinking:
        return name
    return name + "-thinking" + ("" if variant == "greedy" else "-" + variant)


def recap(name, lines, model, thinking=False, variant="greedy"):
    """Recap one transcript. Returns (run record, notes or None); notes is None when the reply can't be read."""
    repo, revision, loader = MODELS[name]
    if variant not in VARIANTS or (variant != "greedy" and not thinking):
        raise ValueError(f"variant {variant!r} needs thinking on")
    if variant == "sampled" and name not in SAMPLING:
        raise ValueError(f"no recommended thinking sampling for {name}")
    budget = THINKING_BUDGET if variant == "budget" else None
    sampling = SAMPLING[name] if variant == "sampled" else None
    max_tokens = MAX_TOKENS if not thinking else BUDGET_MAX_TOKENS if budget else THINKING_MAX_TOKENS
    record = {"run": run_id(name, thinking, variant), "model": name, "repo": repo, "revision": revision,
              "loader": loader, "decoding": "sampled" if sampling else "greedy", "thinking": thinking,
              "max_tokens": max_tokens, "chunk_characters": CHUNK_CHARACTERS}
    if budget:
        record["thinking_budget"] = budget
    if sampling:
        record.update(sampling=sampling, seed=SEED)
    parts = chunks(lines)
    record["chunks"] = len(parts)
    model.reset_peak()
    replies, started = [], time.time()

    def ask(kind, prompt):
        text = model.render(prompt, thinking)
        begun = time.time()
        reply, generated = model.generate(text, max_tokens, budget=budget, sampling=sampling)
        # reply_tokens is the generator's own count: encoding the text again can give fewer tokens than were made.
        replies.append({"kind": kind, "prompt_tokens": model.count(text), "reply_tokens": generated,
                        "seconds": time.time() - begun, "reply": reply})
        if thinking and capped_in_thinking(reply, replies[-1]["reply_tokens"], max_tokens):
            raise ValueError("summary model reached the token cap without closing its thinking")
        return reply

    try:
        notes = [parse_notes(ask("extract", extract_prompt(part, i + 1, len(parts)))) for i, part in enumerate(parts)]
        if len(notes) > 1:
            notes = [parse_notes(ask("merge", merge_prompt(notes)))]
        final = notes[0]
        record.update(status="done", evidence=check_evidence(final, lines))
    except ValueError as error:  # an unreadable reply is a result to report, not a crash
        record.update(status="failed", reason=str(error))
        final = None
    record.update(seconds=time.time() - started, mlx_peak_bytes=model.peak_bytes(), replies=replies)
    return record, final


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def prepare(fixtures, out, cases, convert):
    """Write OUT/<case>/lines.json once; refuse a folder that holds lines from a different transcript."""
    prepared = {}
    for case in cases:
        raw = (fixtures / case / "transcript.json").read_bytes()
        lines = exact_lines(json.loads(raw), convert)
        folder = out / case
        folder.mkdir(parents=True, exist_ok=True)
        data = json.dumps(lines, ensure_ascii=False, indent=1).encode() + b"\n"
        saved = folder / "lines.json"
        if saved.exists() and saved.read_bytes() != data:
            raise ValueError(f"{folder} holds recaps of different transcript lines; use a new folder")
        saved.write_bytes(data)
        (folder / "inputs.json").write_text(json.dumps(
            {"transcript_sha256": sha256(raw), "lines_sha256": sha256(data), "lines": len(lines)}, indent=1) + "\n")
        prepared[case] = lines
    return prepared


def main(argv=None, model_class=Model, convert=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fixtures", type=Path, help="the verified 17-recording synthetic collection")
    parser.add_argument("out", type=Path, help="a new folder outside Git")
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--cases", default=",".join(CASES))
    arm = parser.add_mutually_exclusive_group()
    arm.add_argument("--thinking", action="store_true",
                     help=f"turn the model's thinking on, with a {THINKING_MAX_TOKENS}-token output cap")
    arm.add_argument("--thinking-budget", action="store_true",
                     help=f"thinking on, closed after {THINKING_BUDGET} reply tokens, {BUDGET_MAX_TOKENS}-token cap")
    arm.add_argument("--thinking-sampled", action="store_true",
                     help=f"thinking on with the model card's sampling, seed {SEED}, {THINKING_MAX_TOKENS}-token cap")
    parser.add_argument("--force", action="store_true", help="rerun cases that already have a run.json")
    parser.add_argument("--todo", action="store_true", help="print the cases this run would recap, then stop")
    args = parser.parse_args(argv)
    cases = [c for c in args.cases.split(",") if c]
    missing = [c for c in cases if not (args.fixtures / c / "transcript.json").is_file()]
    if missing:
        parser.error(f"no transcript.json for {', '.join(missing)} in {args.fixtures}")
    if any((p / ".git").exists() for p in [args.out.resolve(), *args.out.resolve().parents]):
        parser.error("OUT must be outside Git: recaps of the collection stay out of the public repository")
    if convert is None:
        from opencc import OpenCC

        convert = OpenCC("s2tw").convert
    try:
        prepared = prepare(args.fixtures, args.out, cases, convert)
    except ValueError as error:
        parser.error(str(error))

    thinking = args.thinking or args.thinking_budget or args.thinking_sampled
    variant = "budget" if args.thinking_budget else "sampled" if args.thinking_sampled else "greedy"
    if variant == "sampled" and args.model not in SAMPLING:
        parser.error(f"--thinking-sampled has no recommended sampling for {args.model}")
    run_name = run_id(args.model, thinking, variant)
    todo = [c for c in cases if args.force or not (args.out / c / run_name / "run.json").exists()]
    if args.todo:
        print("\n".join(todo))
        return
    model = model_class(args.model) if todo else None
    for case in cases:
        if case not in todo:
            print(f"{case} {run_name}: already done, skipping (--force reruns it)")
            continue
        record, notes = recap(args.model, prepared[case], model, thinking, variant)
        folder = args.out / case / run_name
        folder.mkdir(exist_ok=True)
        for stale in ("notes.json", "summary.md", "run.json"):  # an earlier run's files must not outlive it
            (folder / stale).unlink(missing_ok=True)
        if notes is not None:
            (folder / "notes.json").write_text(json.dumps(notes, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            (folder / "summary.md").write_text(summary_markdown(notes), encoding="utf-8")
        # run.json is written last, so its presence means the case finished (done or failed).
        (folder / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{case} {run_name}: {record['status']}" + (f" ({record['reason']})" if "reason" in record else ""))


if __name__ == "__main__":
    sys.exit(main())
