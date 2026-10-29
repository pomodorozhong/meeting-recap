import json
import sys
import unittest

from helpers import SCRIPTS, DatasetCase, write_json

import common


class Validation(unittest.TestCase):
    def test_identifier(self):
        self.assertEqual(common.identifier("run_1-a"), "run_1-a")
        for bad in ["", "-lead", "has space", "a/b", "x" * 65, None, 3]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                common.identifier(bad)

    def test_number_and_span(self):
        self.assertEqual(common.number(0, "n"), 0)
        for bad in [True, "1", float("nan"), float("inf"), -1]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                common.number(bad, "n")
        common.span(0, 1)
        with self.assertRaises(ValueError):
            common.span(2, 2)

    def test_segments(self):
        common.segments([{"speaker_id": "0", "start_seconds": 0, "end_seconds": 1}])
        for bad in [{}, [{"speaker_id": "", "start_seconds": 0, "end_seconds": 1}],
                    [{"speaker_id": "0", "start_seconds": 1, "end_seconds": 0}]]:
            with self.subTest(bad=bad), self.assertRaises((ValueError, KeyError)):
                common.segments(bad)

    def test_read_json_rejects_non_finite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = f"{tmp}/x.json"
            with open(path, "w") as handle:
                handle.write('{"a": NaN}')
            with self.assertRaises(ValueError):
                common.read_json(path)

    def test_write_new_never_overwrites(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            common.write_new(f"{tmp}/a/b.json", {"x": 1})
            with self.assertRaises(FileExistsError):
                common.write_new(f"{tmp}/a/b.json", {"x": 2})

    def test_fingerprint_is_order_independent(self):
        self.assertEqual(common.fingerprint({"a": 1, "b": 2}), common.fingerprint({"b": 2, "a": 1}))


class DatasetPaths(DatasetCase):
    def test_inside_rejects_escape_and_absolute(self):
        self.assertTrue(str(common.inside(self.root, "runs/x")).startswith(str(self.root)))
        for bad in ["../outside", "/etc/passwd", 3]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                common.inside(self.root, bad)

    def test_dataset_rejects_other_formats(self):
        write_json(self.tmp / "other" / "dataset.json", {"format": "something-else", "version": 1})
        with self.assertRaises(ValueError):
            common.dataset(self.tmp / "other")

    def test_recording_rejects_media_outside_dataset(self):
        write_json(self.root / "recordings" / "evil" / "recording.json", {"id": "evil", "media": "../../x.wav"})
        with self.assertRaises(ValueError):
            common.recording(self.root, "evil")


class Events(DatasetCase):
    def setUp(self):
        super().setUp()
        (self.root / "sessions" / "s1").mkdir(parents=True)

    def test_append_numbers_events_and_checks_revision(self):
        first = common.append_event(self.root, "s1", {"type": "answer", "item_id": "c1"})
        second = common.append_event(self.root, "s1", {"type": "answer", "item_id": "c1"}, expected_revision=1)
        self.assertEqual((first["seq"], second["seq"]), (1, 2))
        with self.assertRaises(ValueError):
            common.append_event(self.root, "s1", {"type": "answer", "item_id": "c1"}, expected_revision=1)
        self.assertEqual(common.answers(self.root, "s1")["c1"]["seq"], 2)
        self.assertEqual(common.answers(self.root, "s1", until=1)["c1"]["seq"], 1)

    def test_events_detect_a_gap(self):
        path = self.root / "sessions" / "s1" / "events.jsonl"
        path.write_text(json.dumps({"seq": 1, "type": "x"}) + "\n" + json.dumps({"seq": 3, "type": "x"}) + "\n")
        with self.assertRaises(ValueError):
            common.events(self.root, "s1")


class NoStandardLibraryShadowing(unittest.TestCase):
    def test_script_names_do_not_shadow_stdlib(self):
        # Scripts run with their folder first on sys.path; a script named like a stdlib module
        # (for example select.py) breaks imports such as http.server.
        names = {path.stem for path in SCRIPTS.glob("*.py")}
        self.assertFalse(names & set(sys.stdlib_module_names), names & set(sys.stdlib_module_names))


if __name__ == "__main__":
    unittest.main()
