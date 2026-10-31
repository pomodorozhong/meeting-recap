"""Pure steps of the pipeline: speaker attachment, speaker mapping, Markdown, and summary prompts and checks.

Nothing here loads a model or runs a process, so tests can drive it with generated data.
"""
import json
import re

# Same-speaker words further apart than this become separate turns.
MAX_GAP_SECONDS = 1.0
UNASSIGNED = "__unassigned__"
# Transcript characters per summary chunk; about 15 minutes of a Mandarin call.
CHUNK_CHARACTERS = 6000


def clean(text):
    """Drop Whisper special tokens such as <|zh|>."""
    return re.sub(r"<\|[^|]*\|>", "", text)


def sortformer_segments(raw):
    """Convert fluidaudiocli sortformer --output JSON to segments."""
    segments = [{"speaker_id": s["speaker"].replace(" ", "_"), "start_seconds": float(s["startTimeSeconds"]),
                 "end_seconds": float(s["endTimeSeconds"])} for s in raw["segments"]]
    for s in segments:
        if s["end_seconds"] < s["start_seconds"]:
            raise ValueError(f"diarization segment ends before it starts at {s['start_seconds']} s")
    return sorted(segments, key=lambda s: (s["start_seconds"], s["end_seconds"]))


def label_at(segments, start, end):
    """The label overlapping [start, end] the most; else the nearest within 1 s; else None."""
    best, overlap = None, 0.0
    for segment in segments:
        amount = min(end, segment["end_seconds"]) - max(start, segment["start_seconds"])
        if amount > overlap:
            best, overlap = segment["speaker_id"], amount
    if best is None and segments:
        middle = (start + end) / 2
        distance, best = min((min(abs(middle - s["start_seconds"]), abs(middle - s["end_seconds"])), s["speaker_id"])
                             for s in segments)
        if distance > 1:
            best = None
    return best


def words(asr):
    """Yield (start, end, text) per word, refusing a segment that has text but no word timing."""
    for index, segment in enumerate(asr["segments"]):
        items = segment.get("words")
        if not items:
            if clean(segment.get("text", "")).strip():
                raise ValueError(f"transcript segment {index} has text but no word timestamps")
            continue
        for word in items:
            start, end = float(word["start"]), float(word["end"])
            if end < start:
                raise ValueError(f"transcript segment {index} has a word that ends before it starts")
            text = clean(word["word"])
            if text.strip():
                yield start, end, text


def attach(asr, segments, max_gap=MAX_GAP_SECONDS):
    """Give each word the diarization label it overlaps most, and join a label's nearby words into turns."""
    output, waiting = [], []
    for start, end, text in words(asr):
        if end == start:
            # A zero-length word has no time of its own: it joins the turn just before it, else the next word's.
            if output and not waiting and start - output[-1]["end_seconds"] <= max_gap:
                output[-1]["text"] += text
            else:
                waiting.append((start, text))
            continue
        if waiting:
            text = "".join(t for _, t in waiting) + text
            start = min(start, waiting[0][0])
            waiting = []
        label = label_at(segments, start, end) or UNASSIGNED
        if output and output[-1]["speaker_id"] == label and start - output[-1]["end_seconds"] <= max_gap:
            output[-1]["end_seconds"] = max(output[-1]["end_seconds"], end)
            output[-1]["text"] += text
        else:
            output.append({"speaker_id": label, "start_seconds": start, "end_seconds": end, "text": text})
    if waiting:
        start, text = waiting[0][0], "".join(t for _, t in waiting)
        output.append({"speaker_id": label_at(segments, start, start + 0.01) or UNASSIGNED,
                       "start_seconds": start, "end_seconds": start, "text": text})
    for turn in output:
        turn["text"] = turn["text"].strip()
    return output


def default_speakers(turns):
    """Map each label to Speaker A, B, C... in order of first appearance; unassigned words stay unknown."""
    names, letters = {}, iter("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    for turn in turns:
        label = turn["speaker_id"]
        if label not in names:
            names[label] = "Unknown speaker" if label == UNASSIGNED else f"Speaker {next(letters)}"
    return {"labels": names}


def check_speakers(mapping, turns):
    """Refuse a mapping that leaves a label out or gives one an empty name."""
    labels = mapping.get("labels")
    if not isinstance(labels, dict):
        raise ValueError("speakers.json needs a \"labels\" object mapping each diarization label to a name")
    missing = sorted({t["speaker_id"] for t in turns} - set(labels))
    if missing:
        raise ValueError(f"speakers.json has no name for {', '.join(missing)}")
    for label, name in labels.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"speakers.json gives {label} an empty name")
    return labels


def named_turns(turns, labels, convert=lambda text: text, max_gap=MAX_GAP_SECONDS):
    """Apply the speaker mapping; labels mapped to one name merge, so their adjacent turns join."""
    output = []
    for turn in turns:
        name = labels[turn["speaker_id"]].strip()
        text = convert(turn["text"])
        if output and output[-1]["speaker"] == name and turn["start_seconds"] - output[-1]["end_seconds"] <= max_gap:
            output[-1]["end_seconds"] = max(output[-1]["end_seconds"], turn["end_seconds"])
            output[-1]["text"] += ("" if _joins(output[-1]["text"], text) else " ") + text
        else:
            output.append({"speaker": name, "start_seconds": turn["start_seconds"],
                           "end_seconds": turn["end_seconds"], "text": text})
    return output


def _joins(left, right):
    """Join CJK text without a space; keep a space between Latin words."""
    return not (left[-1:].isascii() and left[-1:].isalnum() and right[:1].isascii() and right[:1].isalnum())


def stamp(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def transcript_markdown(turns, duration_seconds, title="Transcript"):
    speakers = list(dict.fromkeys(t["speaker"] for t in turns))
    lines = [f"# {title}", "", f"- Duration: {stamp(duration_seconds)}",
             f"- Speakers: {', '.join(speakers) if speakers else 'none'}",
             "- Labels come from automatic diarization; rename or merge them in `speakers.json` and run `render`.",
             ""]
    for turn in turns:
        lines += [f"**[{stamp(turn['start_seconds'])}] {turn['speaker']}:** {turn['text']}", ""]
    return "\n".join(lines)


def transcript_lines(turns):
    return [f"[{stamp(t['start_seconds'])}] {t['speaker']}: {t['text']}" for t in turns]


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


def extract_prompt(lines, part=None, parts=None):
    where = f"這是會議逐字稿的第 {part}/{parts} 段。" if parts and parts > 1 else "這是一場會議的逐字稿。"
    return (f"{where}請整理出主題、決議、待辦事項、提議與未解決問題。\n\n{RULES}\n{SCHEMA}\n\n"
            "逐字稿：\n" + "\n".join(lines))


def merge_prompt(notes):
    return ("以下是同一場會議各段逐字稿整理出的 JSON 筆記，依時間順序排列。請合併成一份：合併重複項目並保留所有 evidence 時間戳，"
            "不要新增筆記中沒有的內容。\n\n" + RULES + "\n" + SCHEMA + "\n\n筆記：\n"
            + "\n".join(json.dumps(n, ensure_ascii=False) for n in notes))


SECTIONS = ("topics", "decisions", "action_items", "proposals", "open_questions")


def parse_notes(text):
    """Read the model's JSON object, tolerating a code fence or text around it."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
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
