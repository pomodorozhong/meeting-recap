"""The small-recap-models experiment on generated transcripts, with the model replaced by a fake."""
import contextlib
import hashlib
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


run = load("experiments/small-recap-models/run.py", "small_recap_run")
sys.modules["run"] = run  # scores.py imports run
scores = load("experiments/small-recap-models/scores.py", "small_recap_scores")
pipeline = load("experiments/pipelines/whisper-sortformer/pipeline.py", "pipeline_for_small_recap")
pins = load("experiments/pipelines/whisper-sortformer/pins.py", "pins_for_small_recap")

NOTES = {"topics": [], "decisions": [{"text": "d", "evidence": ["00:00:01", "09:09:09"]}],
         "action_items": [{"task": "t", "owner": None, "due": None, "evidence": []}],
         "proposals": [], "open_questions": []}


class FakeModel:
    instances = []

    def __init__(self, name, reply=None):
        self.name, self.prompts, self.peak_resets = name, [], 0
        self.reply = reply or "```json\n" + json.dumps(NOTES) + "\n```"
        FakeModel.instances.append(self)

    def render(self, prompt, thinking=False):
        return ("T|" if thinking else "N|") + prompt

    def count(self, text):
        return len(text)

    def generate(self, text, max_tokens=None, budget=None, sampling=None):
        self.prompts.append((text, max_tokens))
        self.options = {"budget": budget, "sampling": sampling}
        return self.reply

    def reset_peak(self):
        self.peak_resets += 1

    def peak_bytes(self):
        return 123


def transcript(count):
    return [f"[00:00:{i % 60:02d}] Speaker A: " + "字" * 100 for i in range(count)]


def collection_transcript():
    """A script transcript like the collection's: adjacent turns of one speaker, some Latin words."""
    return {"text": "", "segments": [
        {"start": 0.0, "end": 2.0, "speaker": "A", "text": "我们开始"},
        {"start": 2.5, "end": 4.0, "speaker": "A", "text": "check log"},
        {"start": 4.2, "end": 6.0, "speaker": "A", "text": "timeout 了"},
        {"start": 9.0, "end": 12.0, "speaker": "B", "text": "好，周三前"},
        {"start": 15.0, "end": 16.0, "speaker": "A", "text": "OK"},
    ]}


class MatchesThePipeline(unittest.TestCase):
    def test_prompts_and_chunks(self):
        lines = transcript(3)
        self.assertEqual(run.extract_prompt(lines), pipeline.extract_prompt(lines))
        self.assertEqual(run.extract_prompt(lines, 2, 3), pipeline.extract_prompt(lines, 2, 3))
        self.assertEqual(run.merge_prompt([NOTES]), pipeline.merge_prompt([NOTES]))
        self.assertEqual(run.chunks(transcript(200)), pipeline.chunks(transcript(200)))
        self.assertEqual((run.CHUNK_CHARACTERS, run.MAX_GAP_SECONDS), (pipeline.CHUNK_CHARACTERS, pipeline.MAX_GAP_SECONDS))

    def test_baseline_is_the_pipeline_model(self):
        self.assertEqual(run.MODELS["qwen3.5-9b"][:2], (pins.SUMMARY_REPO, pins.SUMMARY_REVISION))

    def test_exact_lines_match_the_collection_runs_exact_arm(self):
        source = collection_transcript()
        turns = [{"speaker_id": s["speaker"], "start_seconds": s["start"], "end_seconds": s["end"], "text": s["text"]}
                 for s in source["segments"]]
        labels = {t["speaker_id"]: "Speaker " + t["speaker_id"] for t in turns}
        upper = str.upper  # any conversion, applied the same way on both sides
        expected = pipeline.transcript_lines(pipeline.named_turns(turns, labels, upper))
        self.assertEqual(run.exact_lines(source, upper), expected)
        self.assertEqual(len(expected), 3)  # A's first three turns joined

    def test_markdown_and_evidence_checks(self):
        lines = transcript(3)
        ours, theirs = json.loads(json.dumps(NOTES)), json.loads(json.dumps(NOTES))
        self.assertEqual(run.check_evidence(ours, lines), pipeline.check_evidence(theirs, lines))
        self.assertEqual(run.summary_markdown(ours, "Meeting recap"), pipeline.summary_markdown(theirs))


class Recap(unittest.TestCase):
    def test_parse_handles_thinking_fences_and_bad_json(self):
        self.assertEqual(run.parse_notes("<think>a</think>```json\n" + json.dumps(NOTES) + "```")["decisions"][0]["text"], "d")
        self.assertEqual(run.parse_notes("x\n</think>\n" + json.dumps(NOTES))["decisions"][0]["text"], "d")
        gemma = '<|channel>thought\nplan {"not": "this"}<channel|>```json\n' + json.dumps(NOTES) + "\n```"
        self.assertEqual(run.parse_notes(gemma)["decisions"][0]["text"], "d")
        for bad in ("no json here", '{"topics": [}'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                run.parse_notes(bad)

    def test_long_transcript_is_chunked_then_merged(self):
        record, notes = run.recap("gemma4-e2b", transcript(200), FakeModel("gemma4-e2b"))
        self.assertGreater(record["chunks"], 1)
        self.assertEqual([r["kind"] for r in record["replies"]], ["extract"] * record["chunks"] + ["merge"])
        self.assertEqual(record["status"], "done")

    def test_thinking_turns_thinking_on_with_more_room(self):
        model = FakeModel("spark-x2.6-4b")
        record, _ = run.recap("spark-x2.6-4b", transcript(2), model, thinking=True)
        self.assertEqual((record["run"], record["thinking"], record["max_tokens"]),
                         ("spark-x2.6-4b-thinking", True, run.THINKING_MAX_TOKENS))
        self.assertEqual(model.prompts[0][0][:2], "T|")
        self.assertEqual(model.prompts[0][1], run.THINKING_MAX_TOKENS)
        record, _ = run.recap("spark-x2.6-4b", transcript(2), model)
        self.assertEqual((record["run"], record["max_tokens"]), ("spark-x2.6-4b", run.MAX_TOKENS))
        self.assertEqual(model.prompts[1][0][:2], "N|")

    def test_budget_and_sampled_variants(self):
        model = FakeModel("qwen3.5-9b")
        record, _ = run.recap("qwen3.5-9b", transcript(2), model, thinking=True, variant="budget")
        self.assertEqual((record["run"], record["decoding"], record["max_tokens"], record["thinking_budget"]),
                         ("qwen3.5-9b-thinking-budget", "greedy", run.THINKING_BUDGET + run.MAX_TOKENS,
                          run.THINKING_BUDGET))
        self.assertEqual(model.options, {"budget": run.THINKING_BUDGET, "sampling": None})
        record, _ = run.recap("lfm3-1.7b", transcript(2), model, thinking=True, variant="sampled")
        self.assertEqual((record["run"], record["decoding"], record["max_tokens"], record["seed"]),
                         ("lfm3-1.7b-thinking-sampled", "sampled", run.THINKING_MAX_TOKENS, run.SEED))
        self.assertEqual(model.options, {"budget": None, "sampling": run.SAMPLING["lfm3-1.7b"]})
        for args in (("qwen3.5-9b", False, "budget"), ("gemma4-e2b", True, "sampled"), ("qwen3.5-9b", True, "x")):
            with self.subTest(args=args), self.assertRaises(ValueError):
                run.recap(args[0], transcript(2), model, thinking=args[1], variant=args[2])

    def test_reply_capped_inside_its_thinking_is_unreadable(self):
        draft = "<think>" + json.dumps(NOTES)  # a JSON draft inside thinking that never closed
        model = FakeModel("minicpm5-2b", draft)
        model.count = lambda text: run.THINKING_MAX_TOKENS if text == draft else len(text)
        record, notes = run.recap("minicpm5-2b", transcript(2), model, thinking=True, variant="sampled")
        self.assertEqual((record["status"], notes), ("failed", None))
        self.assertIn("without closing its thinking", record["reason"])
        self.assertFalse(run.capped_in_thinking("x</think>" + json.dumps(NOTES), 16384, 16384))
        self.assertFalse(run.capped_in_thinking(draft, 100, 16384))

    def test_unreadable_reply_is_a_failed_result(self):
        record, notes = run.recap("lfm3-1.7b", transcript(2), FakeModel("lfm3-1.7b", "sorry"))
        self.assertEqual((record["status"], notes), ("failed", None))
        self.assertEqual(record["loader"], "mlx-vlm")


class Budget(unittest.TestCase):
    """The thinking budget on real MLX arrays: a vocabulary of 10 tokens, close tag [7, 8], forced [5, 7, 8, 6]."""

    def step(self, processor, tokens):
        import mlx.core as mx

        logits = processor(mx.array(tokens), mx.zeros((1, 10)))
        allowed = [i for i in range(10) if logits[0, i].item() > -float("inf")]
        return allowed[0] if len(allowed) == 1 else None

    def test_forces_the_close_after_the_budget(self):
        processor = run.ThinkingBudget([7, 8], [5, 7, 8, 6], budget=3)
        tokens, forced = [1, 2], []  # the prompt
        for _ in range(8):
            token = self.step(processor, tokens)
            forced.append(token)
            tokens.append(token if token is not None else 3)
        self.assertEqual(forced, [None, None, None, 5, 7, 8, 6, None])

    def test_never_acts_once_the_model_closes_its_thinking(self):
        processor = run.ThinkingBudget([7, 8], [5, 7, 8, 6], budget=4)
        tokens = [1, 2]
        for token in (3, 7, 8, 3, 3, 3, 3):
            self.assertIsNone(self.step(processor, tokens))
            tokens.append(token)
        self.assertTrue(processor.done)


class EntryPoint(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixtures = self.root / "fixtures"
        for case in run.CASES:
            (self.fixtures / case).mkdir(parents=True)
            (self.fixtures / case / "transcript.json").write_text(json.dumps(collection_transcript()))
        FakeModel.instances.clear()

    def run_main(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            run.main([str(self.fixtures), str(self.root / "out"), *extra], model_class=FakeModel,
                     convert=lambda text: text)
        return out.getvalue()

    def test_writes_each_case_and_skips_finished_ones(self):
        self.run_main("--model", "minicpm5-2b")
        for case in run.CASES:
            for file in ("notes.json", "summary.md", "run.json"):
                self.assertTrue((self.root / "out" / case / "minicpm5-2b" / file).exists(), (case, file))
        self.assertEqual(len(FakeModel.instances), 1)
        self.assertIn("already done", self.run_main("--model", "minicpm5-2b"))
        self.assertEqual(len(FakeModel.instances), 1)
        self.run_main("--model", "minicpm5-2b", "--force")
        self.assertEqual(len(FakeModel.instances), 2)

    def test_thinking_arm_writes_beside_the_thinking_off_run(self):
        self.run_main("--model", "minicpm5-2b")
        self.run_main("--model", "minicpm5-2b", "--thinking")
        for name in ("minicpm5-2b", "minicpm5-2b-thinking"):
            record = json.loads((self.root / "out/onboarding" / name / "run.json").read_text())
            self.assertEqual(record["thinking"], name.endswith("-thinking"))
        self.assertEqual(len(FakeModel.instances), 2)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            scores.main(self.root / "out")
        runs = json.loads(out.getvalue())["cases"]["onboarding"]["runs"]
        self.assertEqual(sorted(runs), ["minicpm5-2b", "minicpm5-2b-thinking"])
        self.assertTrue(runs["minicpm5-2b-thinking"]["thinking"])

    def test_later_thinking_variants_write_their_own_runs(self):
        self.run_main("--model", "lfm3-1.7b", "--thinking-budget")
        self.run_main("--model", "lfm3-1.7b", "--thinking-sampled")
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.run_main("--model", "gemma4-e2b", "--thinking-sampled")
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.run_main("--model", "lfm3-1.7b", "--thinking", "--thinking-budget")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            scores.main(self.root / "out")
        runs = json.loads(out.getvalue())["cases"]["onboarding"]["runs"]
        self.assertEqual(sorted(runs), ["lfm3-1.7b-thinking-budget", "lfm3-1.7b-thinking-sampled"])
        self.assertEqual(runs["lfm3-1.7b-thinking-budget"]["thinking_budget"], run.THINKING_BUDGET)
        self.assertEqual(runs["lfm3-1.7b-thinking-sampled"]["sampling"], run.SAMPLING["lfm3-1.7b"])

    def test_refuses_changed_lines_in_the_same_folder(self):
        self.run_main("--model", "minicpm5-2b")
        source = collection_transcript()
        source["segments"][0]["text"] = "changed"
        (self.fixtures / "onboarding" / "transcript.json").write_text(json.dumps(source))
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.run_main("--model", "gemma4-e2b")

    def test_rejects_unknown_models_and_missing_cases(self):
        for extra in (("--model", "nope"), ("--model", "gemma4-e2b", "--cases", "missing")):
            with self.subTest(extra=extra), self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                self.run_main(*extra)

    def test_scores_count_only_grades_of_the_summary_on_disk(self):
        self.run_main("--model", "minicpm5-2b")
        summary = self.root / "out/onboarding/minicpm5-2b/summary.md"
        digest = hashlib.sha256(summary.read_bytes()).hexdigest()
        judgment = {"verdicts": ["full", "partial", "full", "wrong_or_absent"], "supported": [True, True, False, False],
                    "reopens_settled_issue": False, "unsupported_or_garbled_detail": True,
                    "summary_sha256": digest, "notes": "private"}
        (self.root / "out/judgments.json").write_text(json.dumps({"onboarding": {"minicpm5-2b": judgment}}))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            scores.main(self.root / "out")
        result = json.loads(out.getvalue())
        grade = result["cases"]["onboarding"]["runs"]["minicpm5-2b"]["grade"]
        self.assertEqual((grade["full"], grade["partial"], grade["full_and_supported"]), (2, 1, 1))
        self.assertNotIn("private", out.getvalue())
        summary.write_text("changed")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            scores.main(self.root / "out")
        self.assertEqual(json.loads(out.getvalue())["cases"]["onboarding"]["runs"]["minicpm5-2b"]["grade"],
                         {"graded": False, "stale": True})


if __name__ == "__main__":
    unittest.main()
