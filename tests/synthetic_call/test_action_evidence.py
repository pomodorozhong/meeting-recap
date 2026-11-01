import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments/synthetic-call"))
from action_bench import CASES, relabel_lines, speaker_map
from score_actions import count_items, load, summarize


class ActionEvidence(unittest.TestCase):
    def test_fixtures_have_valid_support_and_negative_control(self):
        scripts = [load(p) for p in sorted(CASES.glob("*.json"))]
        self.assertEqual(len(scripts), 10)
        self.assertEqual(sum(len(s["actions"]) for s in scripts), 14)
        self.assertEqual(sum(not s["actions"] for s in scripts), 1)
        for script in scripts:
            labels = set(script["speakers"])
            self.assertEqual(labels, {t["speaker"] for t in script["turns"]})
            self.assertEqual(len(script["actions"]), len({a["id"] for a in script["actions"]}))
            for action in script["actions"]:
                self.assertIn(action["owner"], labels | {None})
                self.assertTrue(action["support_turns"])
                self.assertTrue(all(1 <= i <= len(script["turns"]) for i in action["support_turns"]))

    def test_time_mapping_does_not_reassign_a_merged_label_per_action(self):
        def seg(label, start, end):
            return dict(speaker_id=label, start_seconds=start, end_seconds=end)
        truth = [seg("B", 0, 1), seg("A", 1, 5)]
        self.assertEqual(speaker_map(truth, [seg("x", 0, 5)], {"x": "Speaker B"}), {"Speaker B": "A"})

    def test_label_repair_changes_only_name_and_can_abstain(self):
        lines = ["[00:00:01] Speaker B: first: detail", "[00:00:04] Speaker B: second"]
        turns = [{"start_seconds":1.1, "end_seconds":2.8},{"start_seconds":4.5, "end_seconds":5.0}]
        truth = [{"speaker_id":"C", "start_seconds":0.5, "end_seconds":3.0}]
        self.assertEqual(relabel_lines(lines, turns, truth),
                         ["[00:00:01] Speaker C: first: detail", "[00:00:04] Unknown speaker: second"])

    def test_one_to_one_hits_and_semantically_wrong_or_absent_evidence(self):
        gold = [dict(id="T1", owner="A", due=None)]
        row = {"prediction": {"due": None}, "mapped_owner": "A", "cited_lines": {"00:00:01":["line"]}}
        packet = {"good":row, "bad":dict(row,cited_lines={"00:00:10":[]}), "unrelated":row}
        marks = {k:dict(target="T1", due_ok=True, evidence_ok=k != "unrelated") for k in packet}
        self.assertEqual(count_items(gold, packet, ["bad","unrelated"], marks)["strict_hits"], 0)
        score = summarize(count_items(gold, packet, ["good","good","bad"], marks))
        self.assertEqual((score["strict_hits"],score["false_positives"],score["misses"]), (1,2,0))
        self.assertEqual(score["f1"],0.5)
        empty = summarize(count_items([], {}, [], {}))
        self.assertIsNone(empty["f1"])
        self.assertEqual(empty["false_positives"],0)
