"""Send one call's recap prompt to a running oMLX server twice, the second time as the repeat run.

    uv run --project experiments/omlx experiments/omlx/client.py LINES.json OUT.json --port 8771

Every sampling setting is sent explicitly, because oMLX otherwise fills in the model's recommended ones
(top-k 20 and top-p 0.95 for Qwen), which would not be greedy decoding.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import urllib.request

from common import MAX_TOKENS, extract_prompt, read_lines

MODEL_ID = "qwen3.5-9b"
GREEDY = {"temperature": 0.0, "top_p": 1.0, "top_k": 0, "min_p": 0.0, "repetition_penalty": 1.0,
          "presence_penalty": 0.0, "frequency_penalty": 0.0}


def request_body(lines):
    return {"model": MODEL_ID, "messages": [{"role": "user", "content": extract_prompt(lines)}],
            "max_tokens": MAX_TOKENS, "stream": False, "chat_template_kwargs": {"enable_thinking": False}, **GREEDY}


def post(port, body, timeout=1800):
    request = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                     data=json.dumps(body, ensure_ascii=False).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def main(argv=None, send=post):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lines", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--port", type=int, default=8771)
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args(argv)
    body = request_body(read_lines(args.lines))
    replies = []
    for attempt in range(args.repeats):
        started = time.time()
        answer = send(args.port, body)
        seconds = time.time() - started
        message = answer["choices"][0]["message"]
        usage = answer.get("usage") or {}
        replies.append({"kind": "extract", "attempt": attempt + 1, "seconds": seconds,
                        "reply": message.get("content") or "",
                        "reasoning": message.get("reasoning_content") or message.get("reasoning") or "",
                        "finish_reason": answer["choices"][0].get("finish_reason"),
                        "model": answer.get("model"),
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                        "time_to_first_token": usage.get("time_to_first_token"),
                        "model_load_seconds": usage.get("model_load_duration")})
    args.out.write_text(json.dumps({"runner": "omlx", "request": {k: v for k, v in body.items() if k != "messages"},
                                    "replies": replies}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{args.lines.parent.name}: " + ", ".join(f"{r['seconds']:.1f} s" for r in replies))


if __name__ == "__main__":
    sys.exit(main())
