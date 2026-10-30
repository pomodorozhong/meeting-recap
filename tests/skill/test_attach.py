import json
import unittest

from helpers import DatasetCase, dataset_cli, segs, transcript, write_json

import attach
from common import segments
from scoring import clip_turns

DIARIZATION = segs(("A", 0, 5), ("B", 5, 10))
ASR = transcript(("你", 1, 2), ("好", 2, 3), ("<|zh|>嗨", 6, 7))


class LabelAt(unittest.TestCase):
    def test_largest_overlap_wins(self):
        self.assertEqual(attach.label_at(DIARIZATION, 4, 7), "B")

    def test_nearest_label_within_one_second(self):
        gap = segs(("A", 0, 5), ("B", 8, 10))
        self.assertEqual(attach.label_at(gap, 5.4, 5.6), "A")
        self.assertIsNone(attach.label_at(gap, 6.2, 6.6))


class Turns(unittest.TestCase):
    def test_word_attachment_merges_runs_and_strips_tokens(self):
        out = attach.turns(ASR, DIARIZATION, "word")
        self.assertEqual([(t["speaker_id"], t["text"]) for t in out], [("A", "你好"), ("B", "嗨")])
        self.assertEqual((out[0]["start_seconds"], out[0]["end_seconds"]), (1, 3))

    def test_word_attachment_needs_word_timestamps(self):
        with self.assertRaises(ValueError):
            attach.turns({"segments": [{"start": 0, "end": 1, "text": "x"}]}, DIARIZATION, "word")

    def test_line_attachment_looks_up_the_end_second(self):
        # Ends at 6.5 s, so the end-second lookup finds B although A covers more of the line.
        asr = {"segments": [{"start": 3, "end": 6.5, "text": "x"}]}
        self.assertEqual(attach.turns(asr, DIARIZATION, "line")[0]["speaker_id"], "B")
        self.assertEqual(attach.turns(asr, DIARIZATION, "seg")[0]["speaker_id"], "A")

    def test_unassigned_text(self):
        out = attach.turns(transcript(("x", 20, 21)), DIARIZATION, "word")
        self.assertEqual(out[0]["speaker_id"], "__unassigned__")

    def test_a_silent_gap_splits_one_speakers_turn(self):
        dia = segs(("x", 0, 1), ("x", 100, 101))
        between = attach.turns(transcript(("a", 0, 1), ("b", 100, 101)), dia, "word")
        self.assertEqual([(t["start_seconds"], t["end_seconds"], t["text"]) for t in between], [(0, 1, "a"), (100, 101, "b")])
        self.assertEqual(clip_turns(between, 40, 50), [])
        within = {"segments": [{"start": 0, "end": 101, "text": "ab", "words": [
            {"word": "a", "start": 0, "end": 1}, {"word": "b", "start": 100, "end": 101}]}]}
        self.assertEqual(len(attach.turns(within, dia, "word")), 2)
        close = attach.turns(transcript(("a", 0, 1), ("b", 1.5, 2)), segs(("x", 0, 2)), "word")
        self.assertEqual([(t["start_seconds"], t["end_seconds"], t["text"]) for t in close], [(0, 2, "ab")])

    def test_token_only_words_make_no_turn(self):
        out = attach.turns(transcript(("<|zh|>", 0, 1), ("a", 1, 2), (" ", 2, 3)), DIARIZATION, "word")
        self.assertEqual([(t["start_seconds"], t["end_seconds"], t["text"]) for t in out], [(1, 2, "a")])
        self.assertEqual(attach.turns(transcript(("<|zh|>", 0, 1)), DIARIZATION, "seg"), [])

    def test_text_without_words_is_refused(self):
        timed = transcript(("a", 0, 1))["segments"]
        asr = {"segments": [*timed, {"start": 2, "end": 3, "text": "<|zh|>synthetic words", "words": []}]}
        with self.assertRaisesRegex(ValueError, "segment 1"):
            attach.turns(asr, DIARIZATION, "word")
        silent = {"segments": [*timed, {"start": 2, "end": 3, "text": "<|zh|> ", "words": []}]}
        self.assertEqual([t["text"] for t in attach.turns(silent, DIARIZATION, "word")], ["a"])

    def test_zero_length_words_join_a_neighbouring_turn(self):
        cases = {
            "after a word": ((("a", 1, 2), (",", 2, 2)), [("A", 1, 2, "a,")]),
            "before a word": (((",", 1, 1), ("a", 1, 2)), [("A", 1, 2, ",a")]),
            "a run of them": ((("a", 1, 2), (",", 2, 2), (".", 2, 2), ("b", 2, 3)), [("A", 1, 3, "a,.b")]),
            "between speakers": ((("a", 4, 5), (",", 5, 5), ("b", 5, 6)), [("A", 4, 5, "a,"), ("B", 5, 6, "b")]),
            "a run before a word": (((",", 0.2, 0.2), (".", 0.5, 0.5), ("a", 1, 2)), [("A", 1, 2, ",.a")]),
        }
        for name, (words, expected) in cases.items():
            with self.subTest(name):
                out = attach.turns(transcript(*words), DIARIZATION, "word")
                self.assertEqual([(t["speaker_id"], t["start_seconds"], t["end_seconds"], t["text"]) for t in out], expected)
                segments(out)
        for name, words in {"isolated": [("a", 0, 0)], "far from others": [("a", 1, 2), (",", 8, 8)],
                            "reversed": [("a", 2, 1)],
                            "one far before a word": [(",", 0, 0), (".", 100, 100), ("a", 100.5, 101)]}.items():
            with self.subTest(name), self.assertRaises(ValueError):
                attach.turns(transcript(*words), DIARIZATION, "word")


class Attach(DatasetCase):
    def setUp(self):
        super().setUp()
        self.add_recording("rec1", 30)
        self.add_recording("rec2", 30)
        self.add_run("dia1", artifacts={"segments": DIARIZATION})
        self.add_run("asr1", artifacts={"transcript": ASR})

    def test_creates_a_derived_run(self):
        info = attach.attach(self.root, "asr1", "dia1", "att1", "word")
        self.assertEqual(info["parents"], ["asr1", "dia1"])
        data = json.loads((self.root / info["artifacts"]["segments"]["path"]).read_text())
        self.assertEqual(data[0]["speaker_id"], "A")
        with self.assertRaises(ValueError):
            attach.attach(self.root, "asr1", "dia1", "att1", "word")

    def test_a_racing_attachment_never_deletes_the_winners_run(self):
        real = attach.write_new
        other = {}

        def another_caller_first(path, data):
            # A second caller with the same ID runs to completion just before this caller's first write.
            if not other:
                attach.write_new = real
                try:
                    other["result"] = attach.attach(self.root, "asr1", "dia1", "race", "word")
                except ValueError as error:
                    other["result"] = error
                finally:
                    attach.write_new = another_caller_first
            return real(path, data)
        attach.write_new = another_caller_first
        try:
            try:
                mine = attach.attach(self.root, "asr1", "dia1", "race", "word")
            except (ValueError, OSError) as error:
                mine = error
        finally:
            attach.write_new = real
        outcomes = [isinstance(r, dict) for r in (mine, other["result"])]
        self.assertEqual(sorted(outcomes), [False, True], (mine, other["result"]))
        self.assertTrue((self.root / "runs" / "race" / "run.json").exists())
        dataset_cli.validate(self.root)

    def test_rejects_mismatched_or_changed_parents(self):
        self.add_run("dia2", recording_id="rec2", artifacts={"segments": DIARIZATION})
        with self.assertRaises(ValueError):
            attach.attach(self.root, "asr1", "dia2", "att2", "word")
        self.add_run("dia3", artifacts={"segments": DIARIZATION}, status="failed")
        with self.assertRaises(ValueError):
            attach.attach(self.root, "asr1", "dia3", "att3", "word")
        write_json(self.root / "runs" / "dia1" / "segments.json", segs(("Z", 0, 9)))
        with self.assertRaises(ValueError):
            attach.attach(self.root, "asr1", "dia1", "att4", "word")


if __name__ == "__main__":
    unittest.main()
