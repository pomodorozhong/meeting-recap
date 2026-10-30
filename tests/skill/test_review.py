import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from helpers import DatasetCase, segs, transcript, write_json, write_wav

import evaluate
import review

DIARIZATION = segs(("x", 0, 5), ("y", 5, 10), ("x", 10, 15))
ASR = transcript(("你", 1, 2), ("好", 12, 13))


class ReviewCase(DatasetCase):
    def setUp(self):
        super().setUp()
        self.add_recording("rec1", 30)
        self.add_recording("rec2", 30)
        self.add_run("dia1", artifacts={"segments": DIARIZATION})
        self.add_run("asr1", artifacts={"transcript": ASR})

    def item(self, item_id="c1", **extra):
        return {"id": item_id, "task": "speaker_order", "recording_id": "rec1", "start_seconds": 0,
                "end_seconds": 15, "reason": "turn change", "run_ids": ["dia1"], **extra}

    def plan(self, items=None, session_id="s1"):
        return {"id": session_id, "question": "Who speaks?", "selector": {"name": "agent-selected", "version": "1"},
                "items": items or [self.item(), self.item("c2", task="transcript", run_ids=["asr1"])]}

    def prepare(self, plan=None):
        return review.prepare(self.root, write_json(self.tmp / "plan.json", plan or self.plan()))


class ValidatePlan(ReviewCase):
    def test_accepts_a_good_plan(self):
        self.assertEqual(self.prepare()["format"], "meeting-review-session")
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_rejects_bad_plans(self):
        cases = {
            "no question": {**self.plan(), "question": " "},
            "no items": {**self.plan(), "items": []},
            "no selector version": {**self.plan(), "selector": {"name": "x"}},
            "duplicate item": self.plan([self.item(), self.item()]),
            "bad task": self.plan([self.item(task="summary")]),
            "no reason": self.plan([self.item(reason="")]),
            "past the end": self.plan([self.item(end_seconds=31)]),
            "empty range": self.plan([self.item(start_seconds=5, end_seconds=5)]),
            "other recording's run": self.plan([self.item(recording_id="rec2")]),
            "unknown recording": self.plan([self.item(recording_id="nope", run_ids=[])]),
        }
        for name, plan in cases.items():
            with self.subTest(name), self.assertRaises((ValueError, OSError)):
                review.validate_plan(self.root, plan)


class KnownReference(ReviewCase):
    TRUTH = segs(("A", 0, 4), ("B", 4.2, 6), ("A", 6.3, 12), ("C", 11.5, 13), ("B", 14, 20), ("B", 20.5, 22))

    def known(self, rows=None, reference_id="known1", **extra):
        path = write_json(self.tmp / "truth.json", self.TRUTH if rows is None else rows)
        return review.known_reference(self.root, "rec1", path, reference_id, **extra)

    def test_cuts_clips_at_gaps_and_collapses_turns(self):
        ref = self.known(window=10)
        # The A/C overlap keeps the first clip open until 13 s, where the next gap is.
        self.assertEqual([(c["start_seconds"], c["end_seconds"], c["speaker_order"]) for c in ref["clips"]],
                         [(0, 13, ["A", "B", "A", "C"]), (14, 22, ["B"])])
        self.assertEqual({c["padding_seconds"] for c in ref["clips"]}, {0})
        self.assertEqual((ref["source"]["kind"], ref["excluded"]), ("known_segments", []))
        with self.assertRaises(FileExistsError):
            self.known(window=10)

    def test_scores_a_perfect_run_as_perfect(self):
        self.add_run("truth", artifacts={"segments": self.TRUTH})
        self.known(window=5)
        result = evaluate.evaluate(self.root, "known1", ["truth"], "ev1")["results"][0]
        self.assertEqual((result["turns_recovered"], result["clips_correct"]), (result["reference_turns"], result["clips"]))

    def test_a_turn_too_short_to_score_is_left_out(self):
        rows = segs(("A", 0, 5), ("B", 5, 5.21), ("A", 5.21, 10))
        self.add_run("same", artifacts={"segments": rows})
        ref = self.known(rows, window=30)
        self.assertEqual([c["speaker_order"] for c in ref["clips"]], [["A"]])
        result = evaluate.evaluate(self.root, "known1", ["same"], "ev1")["results"][0]
        self.assertEqual((result["turns_recovered"], result["clips_correct"]), (result["reference_turns"], result["clips"]))
        with self.assertRaises(ValueError):
            evaluate.evaluate(self.root, "known1", ["same"], "ev2", min_overlap=0.1)
        with self.assertRaises(ValueError):
            self.known(segs(("A", 0, 0.2)), reference_id="all-short")

    def test_rejects_bad_segments(self):
        for name, rows in {"empty": [], "past the end": segs(("A", 0, 31)), "blank speaker": segs(("", 0, 1))}.items():
            with self.subTest(name), self.assertRaises(ValueError):
                self.known(rows, reference_id=f"bad{len(name)}")
        with self.assertRaises(ValueError):
            self.known(window=0)


class Predictions(ReviewCase):
    def test_refuses_a_prediction_changed_after_registration(self):
        self.assertEqual([s["speaker_id"] for s in review.prediction(self.root, self.item())["dia1"]], ["x", "y", "x"])
        write_json(self.root / "runs" / "dia1" / "segments.json", segs(("z", 0, 15)))
        with self.assertRaises(ValueError):
            review.prediction(self.root, self.item())


class Answers(ReviewCase):
    def setUp(self):
        super().setUp()
        self.prepare()

    def save(self, **data):
        return review.save_answer(self.root, "s1", {"item_id": "c1", "state": "confirmed", **data})

    def test_saves_speaker_and_transcript_answers(self):
        row = self.save(annotation={"speaker_order": ["A", "B", "A"]}, feedback_text="clear")
        self.assertEqual(row["annotation"], {"speaker_order": ["A", "B", "A"], "allow_extra_turns": False})
        row = review.save_answer(self.root, "s1", {"item_id": "c2", "state": "confirmed", "annotation": {"text": ""}})
        self.assertEqual(row["annotation"], {"text": ""})
        self.assertEqual(self.save(state="unsure")["state"], "unsure")

    def test_rejects_bad_answers(self):
        cases = {
            "unknown item": dict(item_id="c9", annotation={"speaker_order": []}),
            "bad state": dict(state="maybe"),
            "confirmed without order": dict(annotation={}),
            "blank speaker": dict(annotation={"speaker_order": ["A", " "]}),
            "non-boolean extra turns": dict(annotation={"speaker_order": ["A"], "allow_extra_turns": "yes"}),
            "annotation not an object": dict(annotation=["A"]),
            "feedback not text": dict(annotation={"speaker_order": ["A"]}, feedback_text=3),
            "stale revision": dict(annotation={"speaker_order": ["A"]}, expected_revision=5),
        }
        for name, data in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                self.save(**data)
        with self.assertRaises(ValueError):
            review.save_answer(self.root, "s1", {"item_id": "c2", "state": "confirmed", "annotation": {}})

    def test_reference_keeps_only_confirmed_latest_answers(self):
        self.save(annotation={"speaker_order": ["A"]})
        self.save(annotation={"speaker_order": ["A", "B", "A"]})
        review.save_answer(self.root, "s1", {"item_id": "c2", "state": "unsure", "annotation": {}})
        counts = review.close_session(self.root, "s1")["counts"]
        self.assertEqual((counts["confirmed"], counts["unsure"], counts["unreviewed"]), (1, 1, 0))
        ref = review.make_reference(self.root, "s1", "ref1")
        self.assertEqual([c["speaker_order"] for c in ref["clips"]], [["A", "B", "A"]])
        self.assertEqual(ref["excluded"], [{"item_id": "c2", "state": "unsure"}])
        self.assertEqual(ref["revision"], 4)

    def test_reference_reads_answers_and_revision_once(self):
        self.save(annotation={"speaker_order": ["A"]})
        read = review.events

        def save_right_after_the_read(root, session_id):
            rows = read(root, session_id)
            self.save(annotation={"speaker_order": ["A", "B"]})
            return rows
        review.events = save_right_after_the_read
        try:
            ref = review.make_reference(self.root, "s1", "ref-race")
        finally:
            review.events = read
        self.assertEqual(ref["revision"], 1)
        self.assertEqual([(c["answer_seq"], c["speaker_order"]) for c in ref["clips"]], [(1, ["A"])])

    def test_prediction_filters_to_the_clip(self):
        item = self.item(start_seconds=6, end_seconds=9)
        self.assertEqual(review.prediction(self.root, item)["dia1"], segs(("y", 5, 10)))
        text_item = self.item(task="transcript", run_ids=["asr1", "dia1"], start_seconds=10, end_seconds=15)
        result = review.prediction(self.root, text_item)
        self.assertEqual([s["text"] for s in result["asr1"]], ["好"])
        self.assertEqual(result["dia1"], "No compatible prediction artifact")


class Server(ReviewCase):
    def setUp(self):
        super().setUp()
        self.prepare()
        self.token = "test-token"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), review.make_handler(self.root, "s1", self.token))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def request(self, path, body=None, token=True, headers=None, raw=None):
        headers = {**({"X-Review-Token": self.token} if token else {}), **(headers or {})}
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        if data is not None:
            headers.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(self.base + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers), error.read()

    def test_requires_the_token(self):
        self.assertEqual(self.request("/", token=False)[0], 403)
        self.assertEqual(self.request(f"/?token={self.token}", token=False)[0], 200)
        self.assertEqual(self.request("/api/answer", {"item_id": "c1"}, token=False)[0], 403)

    def test_serves_page_session_prediction_and_media(self):
        status, headers, body = self.request("/")
        self.assertEqual((status, headers["Content-Type"]), (200, "text/html; charset=utf-8"))
        self.assertIn(b"Listening review", body)
        self.assertEqual(headers["Cache-Control"], "no-store")
        session = json.loads(self.request("/api/session")[2])
        self.assertEqual((session["revision"], session["closed"]), (0, False))
        self.assertEqual(json.loads(self.request("/api/prediction/c1")[2])["dia1"], DIARIZATION)
        status, headers, body = self.request("/media/c1", headers={"Range": "bytes=0-9"})
        self.assertEqual((status, len(body), headers["Content-Range"].split("/")[0]), (206, 10, "bytes 0-9"))
        status, _, body = self.request("/media/c1")
        self.assertEqual(status, 200)
        self.assertEqual(body[:4], b"RIFF")
        self.assertEqual(self.request("/media/c1", headers={"Range": "bytes=x"})[0], 416)
        self.assertEqual(self.request("/nowhere")[0], 404)
        self.assertEqual(self.request("/api/prediction/c9")[0], 400)

    def test_refuses_to_play_a_recording_changed_after_registration(self):
        self.assertEqual(self.request("/media/c1")[0], 200)
        write_wav(self.root / "recordings" / "rec1" / "source.wav", 31)
        status, _, body = self.request("/media/c1")
        self.assertEqual(status, 400)
        self.assertIn("changed", json.loads(body)["error"])

    def test_saves_answers_and_closes(self):
        answer = {"item_id": "c1", "state": "confirmed", "annotation": {"speaker_order": ["A"]}, "expected_revision": 0}
        status, _, body = self.request("/api/answer", answer)
        self.assertEqual((status, json.loads(body)["seq"]), (200, 1))
        self.assertEqual(self.request("/api/answer", answer)[0], 400)  # stale revision
        self.assertEqual(self.request("/api/answer", {**answer, "expected_revision": None})[0], 400)
        # Finishing from a tab that missed another tab's save must fail like a stale answer does.
        self.assertEqual(self.request("/api/close", {})[0], 400)
        self.assertEqual(self.request("/api/close", {"expected_revision": 0})[0], 400)
        self.assertEqual(json.loads(self.request("/api/close", {"expected_revision": 1})[2])["type"], "close")
        self.assertTrue(json.loads(self.request("/api/session")[2])["closed"])

    def test_rejects_bad_posts(self):
        self.assertEqual(self.request("/api/feedback", {"item_id": "c1"})[0], 404)
        self.assertEqual(self.request("/api/answer", raw=b"{}", headers={"Content-Type": "text/plain"})[0], 400)
        # The server rejects an oversized request from its header, before reading the body.
        import http.client
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.putrequest("POST", "/api/answer")
        for name, value in [("X-Review-Token", self.token), ("Content-Type", "application/json"),
                            ("Content-Length", str(1024 * 1024 + 1))]:
            connection.putheader(name, value)
        connection.endheaders()
        self.assertEqual(connection.getresponse().status, 400)
        connection.close()



PAGE_HARNESS = r"""
const fs = require('fs');
const html = fs.readFileSync(process.argv.at(-1), 'utf8');
const script = html.slice(html.indexOf('<script>') + 8, html.lastIndexOf('</script>'));
// Any element: unknown properties are no-op functions that also accept property reads.
const anything = () => new Proxy(function () {}, {get: (t, k) => (k in t ? t[k] : (t[k] = anything()))});
const audio = {currentTime: 0, paused: true, play() { this.paused = false; this.onplay && this.onplay(); return Promise.resolve(); },
               pause() { this.paused = true; }};
const elements = {audio};
global.document = {getElementById: id => elements[id] || (elements[id] = anything())};
global.window = {addEventListener() {}};
global.location = {search: '?token=t'};
const item = {id: 'c1', task: 'speaker_order', recording_id: 'rec1', start_seconds: 30, end_seconds: 45, padding_seconds: 1};
global.fetch = async () => ({ok: true, json: async () => ({session: {question: 'Who?', items: [item]}, answers: {}, revision: 0, closed: false})});
eval(script);
setTimeout(() => {
  const out = {};
  audio.onloadedmetadata(); out.loaded = audio.currentTime;
  audio.currentTime = 0; audio.play(); out.native_start = audio.currentTime;  // the native Play control
  audio.currentTime = 46.5; audio.ontimeupdate(); out.paused_at_end = audio.paused;
  audio.play(); out.replay_start = audio.currentTime;
  audio.currentTime = 5; audio.ontimeupdate(); out.after_seek_back = audio.currentTime;
  console.log(JSON.stringify(out));
}, 0);
"""


@unittest.skipUnless(__import__("shutil").which("node"), "the page check needs Node")
class PagePlayback(unittest.TestCase):
    def test_native_controls_stay_in_the_clip(self):
        import subprocess

        from helpers import SKILL
        out = subprocess.run(["node", "-e", PAGE_HARNESS, "--", str(SKILL / "assets" / "review.html")],
                             capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out), {"loaded": 29, "native_start": 29, "paused_at_end": True,
                                           "replay_start": 29, "after_seek_back": 29})

if __name__ == "__main__":
    unittest.main()
