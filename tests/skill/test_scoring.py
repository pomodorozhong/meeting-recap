import unittest

from helpers import segs

import scoring


def clip(item_id, start, end, order, **extra):
    return {"id": item_id, "start_seconds": start, "end_seconds": end, "padding_seconds": 0, "speaker_order": order, **extra}


class Lcs(unittest.TestCase):
    def test_lcs(self):
        self.assertEqual(scoring.lcs([], ["a"]), 0)
        self.assertEqual(scoring.lcs(list("abcb"), list("bcab")), 3)


class ClipTurns(unittest.TestCase):
    def test_collapses_repeats_and_ignores_short_overlap(self):
        data = segs(("0", 0, 3), ("0", 3, 4), ("1", 4, 4.2), ("1", 4.2, 6), ("2", 9.9, 12))
        self.assertEqual(scoring.clip_turns(data, 0, 10, min_overlap=0.3), ["0", "1"])
        self.assertEqual(scoring.clip_turns(data, 0, 10, min_overlap=0.05), ["0", "1", "2"])


class Score(unittest.TestCase):
    data = segs(("x", 0, 5), ("y", 5, 10), ("x", 10, 15), ("z", 20, 25))

    def test_best_mapping_recovers_a_perfect_run(self):
        result = scoring.score(self.data, [clip("c1", 0, 15, ["A", "B", "A"])])
        self.assertEqual((result["turns_recovered"], result["clips_correct"]), (3, 1))
        self.assertEqual(result["mapping"], {"x": "A", "y": "B"})
        self.assertEqual(result["mapping_method"], "best_reference_mapping")

    def test_explicit_mapping_and_unmapped_labels(self):
        result = scoring.score(self.data, [clip("c1", 0, 15, ["A", "B", "A"])], mapping={"x": "A"})
        self.assertEqual((result["turns_recovered"], result["clips_correct"]), (2, 0))
        self.assertEqual(result["details"][0]["predicted"], ["A", None, "A"])

    def test_extra_turns_need_permission(self):
        reference = [clip("c1", 0, 15, ["A", "A"])]
        strict = scoring.score(self.data, reference, mapping={"x": "A", "y": "A"})
        self.assertEqual(strict["clips_correct"], 0)
        loose = scoring.score(self.data, [clip("c1", 0, 15, ["A"], allow_extra_turns=True)], mapping={"x": "A", "y": "A"})
        self.assertEqual(loose["clips_correct"], 1)

    def test_unexpected_person_fails_the_clip(self):
        result = scoring.score(self.data, [clip("c1", 0, 10, ["A"], allow_extra_turns=True)], mapping={"x": "A", "y": "B"})
        self.assertEqual(result["clips_correct"], 0)

    def test_padding_widens_the_window(self):
        reference = [clip("c1", 6, 9, ["B", "A"], padding_seconds=2)]
        self.assertEqual(scoring.score(self.data, reference)["turns_recovered"], 2)

    def test_bounds_the_mapping_search(self):
        many = segs(*[(f"l{i}", i, i + 1) for i in range(12)])
        people = [f"P{i}" for i in range(12)]
        with self.assertRaises(ValueError):
            scoring.score(many, [clip("c1", 0, 12, people)])


if __name__ == "__main__":
    unittest.main()
