import unittest

from helpers import DatasetCase, segs, write_json, write_wav

import dataset as dataset_cli


class Init(DatasetCase):
    def test_refuses_inside_a_git_checkout(self):
        (self.tmp / "repo" / ".git").mkdir(parents=True)
        with self.assertRaises(ValueError):
            dataset_cli.init(self.tmp / "repo" / "data")

    def test_refuses_a_non_empty_destination(self):
        write_json(self.tmp / "full" / "x.json", {})
        with self.assertRaises(ValueError):
            dataset_cli.init(self.tmp / "full")


class AddRecording(DatasetCase):
    def test_copies_media_and_records_digest(self):
        info = self.add_recording("rec1", 10, group="call")
        self.assertEqual(info["group"], "call")
        self.assertTrue((self.root / info["media"]).exists())
        self.assertEqual(info["media"], "recordings/rec1/source.wav")

    def test_group_defaults_to_the_id(self):
        self.assertEqual(self.add_recording("rec1", 10)["group"], "rec1")

    def test_rejects_duplicates_bad_extensions_and_durations(self):
        self.add_recording("rec1", 10)
        with self.assertRaises(ValueError):
            self.add_recording("rec1", 10)
        text = write_json(self.tmp / "notes.txt", {})
        with self.assertRaises(ValueError):
            dataset_cli.add_recording(self.root, "rec2", text, 10)
        self.assertFalse((self.root / "recordings" / "rec2").exists())
        audio = write_wav(self.tmp / "a.wav", 1)
        with self.assertRaises(ValueError):
            dataset_cli.add_recording(self.root, "rec3", audio, 0)


class AddRun(DatasetCase):
    def setUp(self):
        super().setUp()
        self.add_recording("rec1", 30)

    def test_copies_artifacts_under_their_names(self):
        info = self.add_run("dia1", artifacts={"segments": segs(("A", 0, 5)), "raw": {"anything": True}})
        self.assertEqual(set(info["artifacts"]), {"segments", "raw"})
        self.assertEqual(info["artifacts"]["segments"]["path"], "runs/dia1/segments.json")

    def test_rejects_bad_specs(self):
        self.add_run("dia1", artifacts={"segments": segs(("A", 0, 5))})
        cases = {
            "duplicate id": dict(run_id="dia1"),
            "unknown recording": dict(run_id="dia2", recording_id="nope"),
            "bad status": dict(run_id="dia3", status="done"),
            "invalid segments": dict(run_id="dia4", artifacts={"segments": segs(("A", 5, 1))}),
        }
        for name, kwargs in cases.items():
            with self.subTest(name), self.assertRaises((ValueError, OSError)):
                self.add_run(**{"artifacts": {"segments": segs(("A", 0, 5))}, **kwargs})
        self.assertFalse((self.root / "runs" / "dia4").exists())

    def test_requires_a_model(self):
        spec = write_json(self.tmp / "s" / "run.json", {"id": "x", "recording_id": "rec1", "model": "", "status": "completed"})
        with self.assertRaises(ValueError):
            dataset_cli.add_run(self.root, spec)


class Validate(DatasetCase):
    def test_counts_and_detects_changes(self):
        self.add_recording("rec1", 30)
        self.add_run("dia1", artifacts={"segments": segs(("A", 0, 5))})
        self.assertEqual(dataset_cli.validate(self.root), {"recordings": 1, "runs": 1, "sessions": 0, "references": 0, "code": 0})
        write_json(self.root / "runs" / "dia1" / "segments.json", segs(("B", 0, 5)))
        with self.assertRaises(ValueError):
            dataset_cli.validate(self.root)

    def test_detects_changed_media(self):
        info = self.add_recording("rec1", 30)
        write_wav(self.root / info["media"], 31)
        with self.assertRaises(ValueError):
            dataset_cli.validate(self.root)


class Snapshot(DatasetCase):
    def test_copies_the_code_once_and_validates_it(self):
        import common
        first = common.snapshot(self.root)
        self.assertEqual(common.snapshot(self.root), first)
        target = self.root / "code" / first["sha256"]
        self.assertTrue((target / "scripts" / "review.py").exists())
        self.assertTrue((target / "assets" / "review.html").exists())
        self.assertEqual(len(list((self.root / "code").iterdir())), 1)
        self.assertEqual(dataset_cli.validate(self.root)["code"], 1)
        (target / "scripts" / "review.py").write_text("# changed\n")
        with self.assertRaises(ValueError):
            dataset_cli.validate(self.root)

    def test_snapshot_runs_from_its_own_copy(self):
        import subprocess
        import sys

        import common
        code = common.snapshot(self.root)["sha256"]
        script = self.root / "code" / code / "scripts" / "dataset.py"
        out = subprocess.run([sys.executable, str(script), "snapshot", str(self.root)], capture_output=True, text=True, check=True)
        self.assertIn(code, out.stdout)


if __name__ == "__main__":
    unittest.main()
