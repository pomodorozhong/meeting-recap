"""Prompt and transcript-line code copied from the pipeline (experiments/pipelines/whisper-sortformer/pipeline.py),
so this folder stands alone; tests/experiments/test_omlx_check.py checks that the copies still match."""
import json
from pathlib import Path

MAX_GAP_SECONDS = 1.0
CHUNK_CHARACTERS = 6000
MAX_TOKENS = 4096  # the stage's output cap (summary_stage.py)
CALLS = ("onboarding", "english-audit", "english-training", "script")


def named_turns(turns, labels, convert=lambda text: text, max_gap=MAX_GAP_SECONDS):
    """Apply the speaker mapping; labels mapped to one name merge, so their adjacent turns join."""
    output = []
    previous_segment = None
    for turn in turns:
        name = labels[turn["speaker_id"]].strip()
        text = convert(turn["text"])
        if (output and output[-1]["speaker"] == name and turn["start_seconds"] - output[-1]["end_seconds"] <= max_gap
                and turn.get("asr_segment") == previous_segment):
            output[-1]["end_seconds"] = max(output[-1]["end_seconds"], turn["end_seconds"])
            output[-1]["text"] += ("" if _joins(output[-1]["text"], text) else " ") + text
        else:
            output.append({"speaker": name, "start_seconds": turn["start_seconds"],
                           "end_seconds": turn["end_seconds"], "text": text})
        previous_segment = turn.get("asr_segment")
    return output


def _joins(left, right):
    """Join CJK text without a space; keep a space between Latin words."""
    return not (left[-1:].isascii() and left[-1:].isalnum() and right[:1].isascii() and right[:1].isalnum())


def stamp(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


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


def exact_lines(transcript, convert):
    """The 2026-11-02 collection run's `exact` arm: the script's turns, each speaker labeled "Speaker <id>"."""
    turns = [{"speaker_id": s["speaker"], "start_seconds": s["start"], "end_seconds": s["end"], "text": s["text"]}
             for s in transcript["segments"]]
    labels = {t["speaker_id"]: "Speaker " + t["speaker_id"] for t in turns}
    return transcript_lines(named_turns(turns, labels, convert))


def read_lines(path):
    """A call's transcript lines; refuse ones that would need the merge step, which this check doesn't cover."""
    lines = json.loads(Path(path).read_text(encoding="utf-8"))
    if len(chunks(lines)) != 1:
        raise ValueError(f"{path} needs more than one chunk; this check covers one-prompt recaps only")
    return lines
