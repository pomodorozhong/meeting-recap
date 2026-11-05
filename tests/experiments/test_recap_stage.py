"""The recap-stage entry point on generated transcripts, with the model replaced by a fake."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / path).rsplit("/", 1)[0])
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


stage = load("experiments/recap-stage/run.py", "recap_stage_run")
pipeline = load("experiments/pipelines/whisper-sortformer/pipeline.py", "pipeline_for_recap_stage")
pins = load("experiments/pipelines/whisper-sortformer/pins.py", "pins_for_recap_stage")

NOTES = {"topics": [], "decisions": [{"text": "d", "evidence": ["00:00:01", "09:09:09"]}],
         "action_items": [{"task": "t", "owner": "unknown", "due": None, "evidence": []}],
         "proposals": [], "open_questions": []}


class FakeModel:
    instances = []

    def __init__(self, reply=None):
        self.prompts, self.peak_resets = [], 0
        self.reply = reply or "<think>x</think>```json\n" + json.dumps(NOTES) + "\n```"
        FakeModel.instances.append(self)

    def render(self, prompt, thinking):
        return f"{'T' if thinking else 'N'}|{prompt}"

    def count(self, text):
        return len(text)

    def generate(self, text, max_tokens):
        self.prompts.append((text, max_tokens))
        return self.reply

    def reset_peak(self):
        self.peak_resets += 1

    def peak_bytes(self):
        return 123


def transcript(count):
    return [f"[00:00:{i % 60:02d}] Speaker A: " + "字" * 100 for i in range(count)]


class Prompts(unittest.TestCase):
    def test_baseline_matches_the_pipeline(self):
        lines = transcript(3)
        self.assertEqual(stage.extract_prompt(lines, 1, 1), pipeline.extract_prompt(lines))
        self.assertEqual(stage.extract_prompt(lines, 2, 3), pipeline.extract_prompt(lines, 2, 3))
        self.assertEqual(stage.merge_prompt([NOTES]), pipeline.merge_prompt([NOTES]))
        self.assertEqual(stage.chunks(transcript(200)), pipeline.chunks(transcript(200)))
        self.assertEqual((stage.MODEL_REPO, stage.MODEL_REVISION), (pins.SUMMARY_REPO, pins.SUMMARY_REVISION))

    def test_noise_variant_only_reorders_the_schema(self):
        a, b = json.loads(stage.SCHEMA), json.loads(stage.SCHEMA_REORDERED)
        self.assertEqual(a, b)
        self.assertNotEqual(list(a), list(b))

    def test_rewritten_prompt_differs_only_where_the_plan_says(self):
        self.assertIn("unknown", stage.RULES_A3)
        self.assertIn("最後", stage.RULES_A3)
        self.assertEqual(json.loads(stage.SCHEMA_A3)["action_items"][0]["owner"], "unknown")

    def test_parse_handles_thinking_and_fences(self):
        self.assertEqual(stage.parse_notes("<think>a</think>```json\n" + json.dumps(NOTES) + "```")["decisions"][0]["text"], "d")
        self.assertEqual(stage.parse_notes("reasoning...\n</think>\n" + json.dumps(NOTES))["decisions"][0]["text"], "d")
        with self.assertRaises(ValueError):
            stage.parse_notes("no json here")


class Variants(unittest.TestCase):
    def test_chunked_variants_merge_and_one_pass_does_not(self):
        lines = transcript(200)  # about 20,000 characters, so four chunks
        chunked, _ = stage.run_variant("A0", lines, FakeModel())
        whole, _ = stage.run_variant("A1", lines, FakeModel())
        self.assertGreater(chunked["chunks"], 1)
        self.assertEqual([r["kind"] for r in chunked["replies"]], ["extract"] * chunked["chunks"] + ["merge"])
        self.assertEqual((whole["chunks"], [r["kind"] for r in whole["replies"]]), (1, ["extract"]))

    def test_thinking_variant_turns_thinking_on_with_more_room(self):
        model = FakeModel()
        record, _ = stage.run_variant("A2", transcript(2), model)
        self.assertTrue(record["thinking"])
        self.assertTrue(model.prompts[0][0].startswith("T|"))
        self.assertEqual(model.prompts[0][1], stage.THINKING_MAX_TOKENS)

    def test_one_pass_over_the_limit_is_reported_not_run_and_never_shortened(self):
        model = FakeModel()
        record, notes = stage.run_variant("A1", transcript(200), model, max_prompt_tokens=1000)
        self.assertEqual(record["status"], "not run")
        self.assertIsNone(notes)
        self.assertEqual(model.prompts, [])

    def test_unparsable_reply_is_a_failed_result_and_evidence_is_checked(self):
        record, notes = stage.run_variant("A0", transcript(2), FakeModel("sorry"))
        self.assertEqual((record["status"], notes), ("failed", None))
        record, notes = stage.run_variant("A0", transcript(2), FakeModel())
        self.assertEqual(record["evidence"], {"evidence_dropped": 1, "items_without_evidence": 1})
        self.assertEqual(notes["decisions"][0]["evidence"], ["00:00:01"])
        self.assertEqual(record["mlx_peak_bytes"], 123)


class EntryPoint(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.transcript = self.root / "t.json"
        self.transcript.write_text(json.dumps(transcript(4), ensure_ascii=False))
        FakeModel.instances.clear()
        self._model = stage.Model
        stage.Model = FakeModel
        self.addCleanup(setattr, stage, "Model", self._model)

    def run_main(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            stage.main([str(self.transcript), str(self.root / "out"), *extra])
        return out.getvalue()

    def test_writes_each_variant_and_skips_finished_ones_on_rerun(self):
        self.run_main("--variants", "A0,A3")
        for name in ("A0", "A3"):
            for file in ("notes.json", "summary.md", "run.json"):
                self.assertTrue((self.root / "out" / name / file).exists(), (name, file))
        inputs = json.loads((self.root / "out/inputs.json").read_text())
        self.assertEqual(inputs["lines"], 4)
        self.assertEqual(len(FakeModel.instances), 1)
        self.assertIn("already done", self.run_main("--variants", "A0,A3"))
        self.assertEqual(len(FakeModel.instances), 1)  # nothing to run, so no model loaded
        self.run_main("--variants", "A0", "--force")
        self.assertEqual(len(FakeModel.instances), 2)

    def test_refuses_a_different_transcript_in_the_same_folder(self):
        self.run_main("--variants", "A0")
        self.transcript.write_text(json.dumps(transcript(5)))
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.run_main("--variants", "A0")

    def test_rejects_bad_input_and_unknown_variants(self):
        for content, extra in (("[]", ()), ('["no stamp"]', ()), (json.dumps(transcript(1)), ("--variants", "A9"))):
            self.transcript.write_text(content)
            with self.subTest(content=content), self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                self.run_main(*extra)


if __name__ == "__main__":
    unittest.main()
