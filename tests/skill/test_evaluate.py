import json
import unittest

from helpers import DatasetCase, segs, write_json

import evaluate
import review


class Evaluate(DatasetCase):
    def setUp(self):
        super().setUp()
        self.add_recording("rec1", 30)
        self.add_recording("rec2", 30)
        self.add_run("good", artifacts={"segments": segs(("x", 0, 5), ("y", 5, 10))})
        self.add_run("merged", artifacts={"segments": segs(("x", 0, 10))})
        self.add_run("other", recording_id="rec2", artifacts={"segments": segs(("x", 0, 10))})
        self.add_run("partial", artifacts={"segments": segs(("x", 0, 10))}, status="incomplete")
        items = [{"id": "c1", "task": "speaker_order", "recording_id": "rec1", "start_seconds": 1, "end_seconds": 9,
                  "padding_seconds": 0, "reason": "turn change", "run_ids": ["good"]},
                 {"id": "c2", "task": "speaker_order", "recording_id": "rec2", "start_seconds": 1, "end_seconds": 9,
                  "padding_seconds": 0, "reason": "turn change", "run_ids": ["other"]},
                 {"id": "c3", "task": "transcript", "recording_id": "rec1", "start_seconds": 1, "end_seconds": 9,
                  "reason": "words", "run_ids": []}]
        review.prepare(self.root, write_json(self.tmp / "plan.json", {
            "id": "s1", "question": "Who speaks?", "selector": {"name": "agent-selected", "version": "1"}, "items": items}))
        for item_id, annotation in [("c1", {"speaker_order": ["A", "B"]}), ("c2", {"speaker_order": ["A"]}), ("c3", {"text": "x"})]:
            review.save_answer(self.root, "s1", {"item_id": item_id, "state": "confirmed", "annotation": annotation})
        review.make_reference(self.root, "s1", "ref1")

    def test_scores_runs_on_one_recording_and_writes_a_report(self):
        result = evaluate.evaluate(self.root, "ref1", ["good", "merged"], "ev1")
        scores = {r["run_id"]: (r["turns_recovered"], r["clips_correct"]) for r in result["results"]}
        self.assertEqual(scores, {"good": (2, 1), "merged": (1, 0)})
        self.assertEqual(result["other_tasks_not_scored"], 1)
        report = (self.root / "evaluations" / "ev1" / "report.md").read_text()
        self.assertIn("| good | 2/2 | 1/1 |", report)
        with self.assertRaises(ValueError):
            evaluate.evaluate(self.root, "ref1", ["good"], "ev1")

    def test_explicit_mapping(self):
        result = evaluate.evaluate(self.root, "ref1", ["good"], "ev2", mappings={"good": {"x": "B", "y": "A"}})
        self.assertEqual(result["results"][0]["turns_recovered"], 1)
        self.assertEqual(result["results"][0]["mapping_method"], "explicit")

    def test_refuses_unfair_or_unsafe_comparisons(self):
        cases = {"incomplete run": ["partial"], "mixed recordings": ["good", "other"], "unknown run": ["nope"]}
        for name, runs in cases.items():
            with self.subTest(name), self.assertRaises((ValueError, OSError)):
                evaluate.evaluate(self.root, "ref1", runs, "bad")
        path = self.root / "references" / "ref1.json"
        data = json.loads(path.read_text())
        data["clips"][0]["speaker_order"] = ["A"]
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            evaluate.evaluate(self.root, "ref1", ["good"], "ev3")

    def test_refuses_a_changed_prediction(self):
        write_json(self.root / "runs" / "good" / "segments.json", segs(("x", 0, 10)))
        with self.assertRaises(ValueError):
            evaluate.evaluate(self.root, "ref1", ["good"], "ev4")


if __name__ == "__main__":
    unittest.main()
