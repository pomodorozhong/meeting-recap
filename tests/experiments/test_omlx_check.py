"""The oMLX check's copied prompt code, client and comparison, with generated text and no server or model."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "experiments/omlx"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / path).rsplit("/", 1)[0])
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


common = load("experiments/omlx/common.py", "common")
sys.modules["common"] = common  # the other scripts import it by this name
client = load("experiments/omlx/client.py", "omlx_client")
compare = load("experiments/omlx/compare.py", "omlx_compare")
pipeline = load("experiments/pipelines/whisper-sortformer/pipeline.py", "pipeline_for_omlx")
pins = load("experiments/pipelines/whisper-sortformer/pins.py", "pins_for_omlx")
control_source = (HERE / "control.py").read_text()

LINES = ["[00:00:00] Speaker A: 我們開始", "[00:00:04] Speaker B: check log 好"]


def collection_transcript():
    return {"text": "", "segments": [
        {"start": 0.0, "end": 2.0, "speaker": "A", "text": "我们开始"},
        {"start": 2.5, "end": 4.0, "speaker": "A", "text": "check log"},
        {"start": 4.2, "end": 6.0, "speaker": "B", "text": "好"},
    ]}


class MatchesThePipeline(unittest.TestCase):
    def test_prompt_and_chunks(self):
        self.assertEqual(common.extract_prompt(LINES), pipeline.extract_prompt(LINES))
        self.assertEqual(common.chunks(LINES * 200), pipeline.chunks(LINES * 200))
        self.assertEqual((common.CHUNK_CHARACTERS, common.MAX_GAP_SECONDS),
                         (pipeline.CHUNK_CHARACTERS, pipeline.MAX_GAP_SECONDS))

    def test_exact_lines(self):
        source = collection_transcript()
        turns = [{"speaker_id": s["speaker"], "start_seconds": s["start"], "end_seconds": s["end"], "text": s["text"]}
                 for s in source["segments"]]
        labels = {t["speaker_id"]: "Speaker " + t["speaker_id"] for t in turns}
        expected = pipeline.transcript_lines(pipeline.named_turns(turns, labels, str.upper))
        self.assertEqual(common.exact_lines(source, str.upper), expected)

    def test_control_uses_the_stage_model_and_cap(self):
        self.assertIn(f'MODEL_REPO = "{pins.SUMMARY_REPO}"', control_source)
        self.assertIn(f'MODEL_REVISION = "{pins.SUMMARY_REVISION}"', control_source)
        stage = (ROOT / "experiments/pipelines/whisper-sortformer/summary_stage.py").read_text()
        self.assertIn(f"MAX_TOKENS = {common.MAX_TOKENS}", stage)


class Client(unittest.TestCase):
    def test_request_is_greedy_with_thinking_off(self):
        body = client.request_body(LINES)
        self.assertEqual(body["messages"][0]["content"], pipeline.extract_prompt(LINES))
        self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual((body["temperature"], body["top_p"], body["top_k"], body["repetition_penalty"]),
                         (0.0, 1.0, 0, 1.0))
        self.assertEqual(body["max_tokens"], 4096)

    def test_sends_twice_and_records_usage(self):
        sent = []

        def send(port, body):
            sent.append(body)
            return {"model": "qwen3.5-9b", "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 2,
                              "prompt_tokens_details": {"cached_tokens": 8 if sent[1:] else 0}}}

        with tempfile.TemporaryDirectory() as temp:
            lines, out = Path(temp) / "lines.json", Path(temp) / "omlx.json"
            lines.write_text(json.dumps(LINES, ensure_ascii=False))
            with contextlib.redirect_stdout(io.StringIO()):
                client.main([str(lines), str(out)], send=send)
            replies = json.loads(out.read_text())["replies"]
        self.assertEqual(len(sent), 2)
        self.assertEqual([r["cached_tokens"] for r in replies], [0, 8])

    def test_refuses_lines_that_need_a_merge(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lines.json"
            path.write_text(json.dumps(["[00:00:00] Speaker A: " + "字" * 100] * 100, ensure_ascii=False))
            with self.assertRaises(ValueError):
                common.read_lines(path)


class Compare(unittest.TestCase):
    def write(self, folder, name, replies, peak=None):
        (folder / f"{name}.json").write_text(json.dumps({"replies": [{"reply": r} for r in replies]}))
        if peak:
            (folder / f"{name}.time").write_text(f"  12.5 real  1 user\n  {peak}  peak memory footprint\n")

    def test_reports_matches_differences_and_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            same, other = out / "onboarding", out / "script"
            for folder in (same, other):
                folder.mkdir()
                (folder / "omlx-models.json").write_text(json.dumps({"data": [{"id": "qwen3.5-9b"}]}))
            self.write(same, "stage", ['{"a": 1}'])
            self.write(same, "control", ['{"a": 1}'])
            self.write(same, "omlx", ['{"a": 1}', '{"a": 1}'], peak=5000)
            self.write(other, "stage", ['{"a": 1}'])
            self.write(other, "control", ['{"a": 2}'])
            self.write(other, "omlx", ['{"a": 2}', '<think>x</think>{"a": 2}'], peak=6000)
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                compare.main(out)
        result = json.loads(printed.getvalue())
        self.assertTrue(result["calls"]["onboarding"]["omlx_first_matches_stage"])
        script = result["calls"]["script"]
        self.assertEqual((script["omlx_first_matches_stage"], script["omlx_first_differs_from_stage_at"],
                          script["omlx_first_matches_control"], script["omlx_repeat_matches_first"]),
                         (False, 6, True, False))
        self.assertEqual(result["checks"], {"same_output": False, "pinned_revision": True,
                                            "memory_readable": True, "thinking_off": False})
        self.assertNotIn('\\"a\\"', printed.getvalue())  # digests only: no reply text


if __name__ == "__main__":
    unittest.main()
