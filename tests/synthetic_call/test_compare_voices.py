"""The voice comparison page lists every call and which versions can play each turn."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
import compare_voices as compare


def make_call(folder, name, turns, voices, missing_turns=()):
    """Write a generated call in the collection's layout, with empty audio files."""
    call = folder / name
    (call / "turns").mkdir(parents=True)
    (call / "call.wav").write_bytes(b"")
    segments = [{"speaker": speaker, "text": text} for speaker, text in turns]
    (call / "transcript.json").write_text(json.dumps({"segments": segments}))
    (call / "manifest.json").write_text(json.dumps({
        "language": "zh", "duration_seconds": 12.5,
        "speakers": {speaker: {"voice": voice} for speaker, voice in voices.items()}}))
    for number, (speaker, _) in enumerate(turns, 1):
        if number not in missing_turns:
            (call / "turns" / f"{number:02d}-{speaker}.wav").write_bytes(b"")


class CompareVoices(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.current, self.new = self.root / "current", self.root / "new"
        turns = [("A", "你好"), ("B", "log 呢？")]
        make_call(self.current, "design", turns, {"A": "dylan", "B": "f5-news-female"})
        make_call(self.new, "design", turns, {"A": "dylan", "B": "f5-news-female"}, missing_turns={2})
        make_call(self.current, "stocktake", [("A", "盤點")], {"A": "aiden"})

    def tearDown(self):
        self.temporary.cleanup()

    def versions(self):
        return compare.parse_versions([f"current={self.current}", f"new={self.new}"])

    def test_versions_keep_their_order_and_need_two_clean_labels(self):
        self.assertEqual(list(self.versions()), ["current", "new"])
        for pairs in ([f"current={self.current}"], [f"Current={self.current}", f"new={self.new}"],
                      [f"a={self.current}", f"a={self.new}"], [f"a={self.current}", "b"],
                      [f"a={self.current}", f"b={self.root / 'absent'}"]):
            with self.assertRaises(ValueError, msg=pairs):
                compare.parse_versions(pairs)

    def test_each_turn_lists_the_versions_that_have_it(self):
        calls = {call["name"]: call for call in compare.collect(self.versions())}
        design = calls["design"]
        self.assertEqual(design["versions"], ["current", "new"])
        self.assertEqual([turn["have"] for turn in design["turns"]], [["current", "new"], ["current"]])
        self.assertEqual(design["turns"][1]["file"], "turns/02-B.wav")
        self.assertEqual(design["speakers"], {"A": "dylan", "B": "f5-news-female"})
        self.assertEqual(calls["stocktake"]["versions"], ["current"])

    def test_recordings_not_voiced_from_a_script_are_left_out(self):
        silence = self.current / "silence"
        silence.mkdir()
        (silence / "call.wav").write_bytes(b"")
        (silence / "transcript.json").write_text(json.dumps({"segments": []}))
        (silence / "manifest.json").write_text(json.dumps({"condition": "silence", "duration_seconds": 12.0}))
        self.assertNotIn("silence", [call["name"] for call in compare.collect(self.versions())])

    def test_handoff_marks_the_gate_turns(self):
        self.assertEqual(compare.gate_turns("handoff"), {6: "gate: “log”", 10: "gate: “timeout”"})
        self.assertEqual(compare.gate_turns("design"), {})

    def test_build_links_versions_and_replaces_an_earlier_build(self):
        out = self.root / "page"
        compare.build(out, self.versions())
        compare.build(out, {"current": self.current, "other": self.new})
        self.assertEqual(sorted(path.name for path in out.iterdir()), ["current", "data.js", "index.html", "other"])
        self.assertEqual((out / "other").resolve(), self.new.resolve())
        data = json.loads((out / "data.js").read_text().removeprefix("window.COMPARISON = ").rstrip(";\n"))
        self.assertEqual(data["versions"], ["current", "other"])


if __name__ == "__main__":
    unittest.main()
