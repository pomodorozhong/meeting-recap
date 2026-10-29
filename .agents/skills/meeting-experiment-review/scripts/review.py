#!/usr/bin/env python3
"""Freeze agent-selected questions, collect local feedback, and snapshot confirmed references."""
from __future__ import annotations

import argparse
import json
import mimetypes
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from common import (answers, append_event, dataset, events, fingerprint, identifier, inside,
                    now, number, read_json, recording, run, session, span, write_new)

TASKS = {"speaker_order", "transcript"}
STATES = {"confirmed", "unsure", "skipped", "unusable"}


def validate_plan(root, plan):
    identifier(plan["id"])
    if not isinstance(plan.get("question"), str) or not plan["question"].strip():
        raise ValueError("session question is required")
    if not isinstance(plan.get("items"), list) or not plan["items"]:
        raise ValueError("session needs review items")
    selector = plan.get("selector", {})
    if not selector.get("name") or not selector.get("version"):
        raise ValueError("selector name and version are required; use agent-selected for manual selection")
    seen = set()
    for item in plan["items"]:
        identifier(item["id"])
        if item["id"] in seen:
            raise ValueError("duplicate item ID")
        seen.add(item["id"])
        if item.get("task") not in TASKS:
            raise ValueError("task must be speaker_order or transcript")
        if not isinstance(item.get("reason"), str) or not item["reason"].strip():
            raise ValueError("each selection needs a reason")
        rec = recording(root, item["recording_id"])
        span(item["start_seconds"], item["end_seconds"])
        if item["end_seconds"] > rec["duration_seconds"]:
            raise ValueError("review range exceeds recording duration")
        number(item.get("padding_seconds", 1), "padding_seconds")
        for run_id in item.get("run_ids", []):
            if run(root, run_id)["recording_id"] != item["recording_id"]:
                raise ValueError("item and prediction run name different recordings")
    return plan


def prepare(root, plan_path):
    plan = validate_plan(root, read_json(plan_path))
    result = {**plan, "format": "meeting-review-session", "version": 1, "created_at": now()}
    write_new(root / "sessions" / plan["id"] / "session.json", result)
    return result


def save_answer(root, session_id, data):
    plan = session(root, session_id)
    item = next((item for item in plan["items"] if item["id"] == data.get("item_id")), None)
    if item is None:
        raise ValueError("unknown review item")
    state = data.get("state")
    if state not in STATES:
        raise ValueError("choose confirmed, unsure, skipped, or unusable")
    annotation = data.get("annotation", {})
    if not isinstance(annotation, dict):
        raise ValueError("annotation must be an object")
    clean = {}
    if item["task"] == "speaker_order":
        order = annotation.get("speaker_order")
        if state == "confirmed" and not isinstance(order, list):
            raise ValueError("confirmed speaker answers need an explicit speaker_order array (empty for no speech)")
        if order is not None:
            if not isinstance(order, list) or not all(isinstance(s, str) and s.strip() for s in order):
                raise ValueError("speaker_order must be an array of nonempty speaker IDs")
            clean["speaker_order"] = order
        if not isinstance(annotation.get("allow_extra_turns", False), bool):
            raise ValueError("allow_extra_turns must be boolean")
        clean["allow_extra_turns"] = annotation.get("allow_extra_turns", False)
    else:
        text = annotation.get("text")
        if state == "confirmed" and not isinstance(text, str):
            raise ValueError("confirmed transcript answers need explicit text (empty for no speech)")
        if text is not None:
            if not isinstance(text, str):
                raise ValueError("transcript text must be a string")
            clean["text"] = text
    feedback = data.get("feedback_text", "")
    if not isinstance(feedback, str):
        raise ValueError("feedback_text must be text")
    return append_event(root, session_id, {"type": "answer", "item_id": item["id"], "state": state,
                                          "annotation": clean, "feedback_text": feedback}, data.get("expected_revision"))


def make_reference(root, session_id, reference_id):
    identifier(reference_id)
    plan = session(root, session_id)
    rows = events(root, session_id)
    latest = answers(root, session_id)
    clips, excluded = [], []
    for item in plan["items"]:
        answer = latest.get(item["id"])
        if answer is None or answer["state"] != "confirmed":
            excluded.append({"item_id": item["id"], "state": answer["state"] if answer else "unreviewed"})
            continue
        clips.append({**item, **answer["annotation"], "answer_seq": answer["seq"]})
    info = {"format": "meeting-review-reference", "version": 1, "id": reference_id,
            "session_id": session_id, "session_sha256": fingerprint(plan),
            "events_sha256": fingerprint(rows), "revision": len(rows), "created_at": now(),
            "clips": clips, "excluded": excluded}
    result = {**info, "sha256": fingerprint(info)}
    write_new(root / "references" / (reference_id + ".json"), result)
    return result


def close_session(root, session_id):
    plan = session(root, session_id)
    latest = answers(root, session_id)
    counts = {state: 0 for state in [*sorted(STATES), "unreviewed"]}
    for item in plan["items"]:
        counts[latest.get(item["id"], {}).get("state", "unreviewed")] += 1
    return append_event(root, session_id, {"type": "close", "counts": counts})


def prediction(root, item):
    result = {}
    for run_id in item.get("run_ids", []):
        info = run(root, run_id)
        artifact = info["artifacts"].get("segments" if item["task"] == "speaker_order" else "transcript")
        if not artifact:
            result[run_id] = "No compatible prediction artifact"
            continue
        data = read_json(inside(root, artifact["path"]))
        if item["task"] == "speaker_order":
            data = [{"speaker_id": s["speaker_id"], "start_seconds": s["start_seconds"], "end_seconds": s["end_seconds"]}
                    for s in data if s["start_seconds"] < item["end_seconds"] and s["end_seconds"] > item["start_seconds"]]
        else:
            data = [s for s in data["segments"] if s["start"] < item["end_seconds"] and s["end"] > item["start_seconds"]]
        result[run_id] = data
    return result


def make_handler(root, session_id, token):
    plan = session(root, session_id)
    items = {item["id"]: item for item in plan["items"]}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Do not copy dataset content, URLs, or access tokens into terminal logs.

        def authorized(self):
            query = parse_qs(urlparse(self.path).query)
            supplied = self.headers.get("X-Review-Token") or query.get("token", [""])[0]
            return secrets.compare_digest(supplied, token)

        def send_data(self, data, content_type="application/json", status=200):
            body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode() if content_type == "application/json" else data
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.authorized():
                self.send_data({"error": "open the local URL printed by the review command"}, status=403)
                return
            path = urlparse(self.path).path
            try:
                if path == "/":
                    html = (Path(__file__).parent.parent / "assets" / "review.html").read_bytes()
                    self.send_data(html, "text/html; charset=utf-8")
                elif path == "/api/session":
                    rows = events(root, session_id)
                    self.send_data({"session": plan, "answers": answers(root, session_id), "revision": len(rows),
                                    "closed": any(row["type"] == "close" for row in rows)})
                elif path.startswith("/api/prediction/"):
                    self.send_data(prediction(root, items[path.rsplit("/", 1)[1]]))
                elif path.startswith("/media/"):
                    item = items[path.rsplit("/", 1)[1]]
                    self.send_media(inside(root, recording(root, item["recording_id"])["media"]))
                else:
                    self.send_data({"error": "not found"}, status=404)
            except (ValueError, KeyError, OSError, TypeError) as error:
                self.send_data({"error": str(error)}, status=400)

        def send_media(self, source):
            size = source.stat().st_size
            start, end = 0, size - 1
            requested = self.headers.get("Range")
            if requested:
                import re
                match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested)
                if not match or not any(match.groups()):
                    self.send_data({"error": "unsupported byte range"}, status=416)
                    return
                a, b = match.groups()
                if a:
                    start, end = int(a), min(int(b), end) if b else end
                else:
                    start = max(0, size - int(b))
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
            self.send_response(206 if requested else 200)
            self.send_header("Content-Type", mimetypes.guess_type(source)[0] or "application/octet-stream")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Cache-Control", "no-store")
            if requested:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            with source.open("rb") as handle:
                handle.seek(start)
                remaining = end - start + 1
                while remaining:
                    block = handle.read(min(65536, remaining))
                    if not block:
                        break
                    self.wfile.write(block)
                    remaining -= len(block)

        def do_POST(self):
            if not self.authorized():
                self.send_data({"error": "invalid review token"}, status=403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 1024 * 1024:
                    raise ValueError("request must be 1 byte–1 MiB")
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError("JSON request required")
                data = json.loads(self.rfile.read(length))
                path = urlparse(self.path).path
                if path == "/api/answer":
                    if not isinstance(data.get("expected_revision"), int):
                        raise ValueError("expected_revision is required")
                    result = save_answer(root, session_id, data)
                elif path == "/api/close":
                    result = close_session(root, session_id)
                else:
                    self.send_data({"error": "not found"}, status=404)
                    return
                self.send_data(result)
            except (ValueError, KeyError, OSError, TypeError) as error:
                self.send_data({"error": str(error)}, status=400)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "serve", "answer", "reference", "close"):
        cmd = sub.add_parser(name)
        cmd.add_argument("dataset")
        if name == "prepare":
            cmd.add_argument("--plan", required=True)
        else:
            cmd.add_argument("--session", required=True)
        if name == "serve":
            cmd.add_argument("--port", type=int, default=0)
        elif name == "answer":
            cmd.add_argument("--file", required=True, help="private JSON containing an explicitly confirmed user answer")
        elif name == "reference":
            cmd.add_argument("--id", required=True)
    args = parser.parse_args()
    root = dataset(args.dataset)
    if args.command == "prepare":
        result = prepare(root, args.plan)
    elif args.command == "answer":
        result = save_answer(root, args.session, read_json(args.file))
    elif args.command == "reference":
        result = make_reference(root, args.session, args.id)
    elif args.command == "close":
        result = close_session(root, args.session)
    else:
        token = secrets.token_urlsafe(32)
        server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(root, args.session, token))
        print(f"Local review: http://127.0.0.1:{server.server_port}/?token={token}", flush=True)
        print("Ctrl-C stops the server. Answers stay in the private dataset.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        sys.exit(str(error))
