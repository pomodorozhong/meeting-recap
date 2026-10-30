import unittest

from helpers import DatasetCase, segs, write_json, write_wav

import common
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


class PrivateLocation(DatasetCase):
    def test_refuses_writes_to_a_dataset_inside_a_git_checkout(self):
        import shutil
        import subprocess
        import sys

        import common
        from helpers import SCRIPTS
        self.add_recording("rec1", 10)
        checkout = self.tmp / "repo"
        checkout.mkdir()
        (checkout / ".git").write_text("gitdir: elsewhere\n")  # a worktree's marker is a file
        shutil.copytree(self.root, checkout / "data")
        (self.tmp / "link").symlink_to(checkout / "data")
        for path in (checkout / "data", self.tmp / "link"):
            with self.subTest(str(path.name)):
                with self.assertRaises(ValueError):
                    common.dataset(path)
                self.assertEqual(common.dataset(path, write=False), (checkout / "data").resolve())
                script = [sys.executable, str(SCRIPTS / "dataset.py")]
                self.assertEqual(subprocess.run([*script, "validate", str(path)], capture_output=True).returncode, 0)
                refused = subprocess.run([*script, "snapshot", str(path)], capture_output=True, text=True)
                self.assertIn("outside any Git checkout", refused.stderr)
        self.assertFalse((checkout / "data" / "code").exists())


class SymlinkedSubdirectory(DatasetCase):
    """A dataset folder that is a symlink must not carry private writes out of the dataset."""

    def setUp(self):
        super().setUp()
        import evaluate
        import review
        self.evaluate, self.review = evaluate, review
        self.add_recording("rec1", 30)
        self.add_run("dia1", artifacts={"segments": segs(("x", 0, 5))})
        review.prepare(self.root, write_json(self.tmp / "plan.json", {
            "id": "s1", "question": "Who speaks?", "selector": {"name": "agent-selected", "version": "1"},
            "items": [{"id": "c1", "task": "speaker_order", "recording_id": "rec1", "start_seconds": 1,
                       "end_seconds": 4, "padding_seconds": 0, "reason": "turn", "run_ids": ["dia1"]}]}))
        self.answer()
        review.make_reference(self.root, "s1", "ref1")
        evaluate.evaluate(self.root, "ref1", ["dia1"], "ev1")
        self.checkout = self.tmp / "checkout"
        (self.checkout / ".git").mkdir(parents=True)

    def answer(self):
        self.review.save_answer(self.root, "s1", {"item_id": "c1", "state": "confirmed",
                                                  "annotation": {"speaker_order": ["A"]}})

    def test_refuses_writes_through_a_symlinked_folder(self):
        import shutil
        writes = {
            "recordings": lambda: self.add_recording("rec2", 10),
            "runs": lambda: self.add_run("dia2", artifacts={"segments": segs(("x", 0, 5))}),
            "sessions": self.answer,
            "references": lambda: self.review.make_reference(self.root, "s1", "ref2"),
            "evaluations": lambda: self.evaluate.evaluate(self.root, "ref1", ["dia1"], "ev2"),
            "code": lambda: common.snapshot(self.root),
        }
        for name, write in writes.items():
            for destination in (self.checkout / name, self.tmp / "elsewhere" / name):
                with self.subTest(name, to=destination.parent.name):
                    folder = self.root / name
                    destination.parent.mkdir(exist_ok=True)
                    shutil.move(folder, destination)
                    if name == "code":
                        shutil.rmtree(destination)
                        destination.mkdir()
                    before = sorted(p.relative_to(destination) for p in destination.rglob("*"))
                    folder.symlink_to(destination)
                    try:
                        with self.assertRaises(ValueError):
                            write()
                        self.assertEqual(sorted(p.relative_to(destination) for p in destination.rglob("*")), before)
                    finally:
                        folder.unlink()
                        shutil.move(destination, folder)
                        if name == "code":
                            common.snapshot(self.root)


    def test_refuses_answers_through_a_symlinked_log_or_lock(self):
        import shutil
        for name in ("events.jsonl", ".lock"):
            with self.subTest(name):
                log = self.root / "sessions" / "s1" / name
                outside = self.checkout / name
                shutil.move(log, outside)
                before = outside.read_bytes()
                log.symlink_to(outside)
                try:
                    with self.assertRaises(ValueError):
                        self.answer()
                    self.assertEqual(outside.read_bytes(), before)
                finally:
                    log.unlink()
                    shutil.move(outside, log)


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
        self.assertEqual(dataset_cli.validate(self.root), {"recordings": 1, "runs": 1, "sessions": 0, "references": 0,
                                                         "evaluations": 0, "unsealed_evaluations": [], "code": 0})
        write_json(self.root / "runs" / "dia1" / "segments.json", segs(("B", 0, 5)))
        with self.assertRaises(ValueError):
            dataset_cli.validate(self.root)

    def test_detects_changed_media(self):
        info = self.add_recording("rec1", 30)
        write_wav(self.root / info["media"], 31)
        with self.assertRaises(ValueError):
            dataset_cli.validate(self.root)


class ValidateProvenance(DatasetCase):
    def setUp(self):
        super().setUp()
        import evaluate
        import review
        self.review = review
        self.add_recording("rec1", 30)
        self.add_run("dia1", artifacts={"segments": segs(("x", 0, 5), ("y", 5, 10))})
        review.prepare(self.root, write_json(self.tmp / "plan.json", {
            "id": "s1", "question": "Who speaks?", "selector": {"name": "agent-selected", "version": "1"},
            "items": [{"id": "c1", "task": "speaker_order", "recording_id": "rec1", "start_seconds": 1,
                       "end_seconds": 9, "padding_seconds": 0, "reason": "turn change", "run_ids": ["dia1"]}]}))
        self.answer(["A", "B"])
        review.make_reference(self.root, "s1", "ref1")
        evaluate.evaluate(self.root, "ref1", ["dia1"], "ev1")

    def answer(self, order):
        self.review.save_answer(self.root, "s1", {"item_id": "c1", "state": "confirmed", "annotation": {"speaker_order": order}})

    def test_detects_each_change_to_evidence_or_results(self):
        import json

        def edit_json(name, change):
            def apply(path):
                data = json.loads(path.read_text())
                change(data)
                path.write_text(json.dumps(data))
            return name, apply

        def edit_text(name, old, new):
            return name, lambda path: path.write_text(path.read_text().replace(old, new))

        mutations = {
            "evaluation result": edit_json("evaluations/ev1/evaluation.json",
                                           lambda d: d["results"][0].update(clips_correct=0)),
            "evaluation report": edit_text("evaluations/ev1/report.md", "| 2/2 | 1/1 |", "| 0/2 | 0/1 |"),
            "session question": edit_json("sessions/s1/session.json", lambda d: d.update(question="Who else?")),
            "referenced answer": edit_text("sessions/s1/events.jsonl", '["A", "B"]', '["B", "A"]'),
            "evaluated run": edit_json("runs/dia1/run.json", lambda d: d.update(notes="changed")),
        }
        self.assertEqual(dataset_cli.validate(self.root)["evaluations"], 1)
        for name, (relative, apply) in mutations.items():
            path = self.root / relative
            original = path.read_bytes()
            with self.subTest(name):
                apply(path)
                self.assertNotEqual(path.read_bytes(), original)
                with self.assertRaises(ValueError):
                    dataset_cli.validate(self.root)
            path.write_bytes(original)

    def test_answers_after_the_reference_keep_it_valid(self):
        self.answer(["B"])
        self.review.close_session(self.root, "s1")
        self.assertEqual(dataset_cli.validate(self.root)["references"], 1)

    def test_lists_evaluations_saved_before_they_were_sealed(self):
        import json
        path = self.root / "evaluations" / "ev1" / "evaluation.json"
        data = json.loads(path.read_text())
        del data["sha256"], data["report_sha256"]
        path.write_text(json.dumps(data))
        self.assertEqual(dataset_cli.validate(self.root)["unsealed_evaluations"], ["ev1"])


class Snapshot(DatasetCase):
    def test_copies_the_code_once_and_validates_it(self):
        import common
        first = common.snapshot(self.root)
        self.assertEqual(common.snapshot(self.root), first)
        target = self.root / "code" / first["sha256"]
        self.assertTrue((target / "scripts" / "review.py").exists())
        self.assertTrue((target / "assets" / "review.html").exists())
        # The locked environment (OpenCC for transcript clips) is part of what reproduces a step.
        self.assertTrue((target / "pyproject.toml").exists() and (target / "uv.lock").exists())
        self.assertEqual(len(list((self.root / "code").iterdir())), 1)
        self.assertEqual(dataset_cli.validate(self.root)["code"], 1)
        (target / "scripts" / "review.py").write_text("# changed\n")
        with self.assertRaises(ValueError):
            dataset_cli.validate(self.root)

    def test_concurrent_snapshots_share_one_copy(self):
        import subprocess
        import sys

        from helpers import SCRIPTS
        code = f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); import common, pathlib; " \
               f"print(common.snapshot(pathlib.Path({str(self.root)!r}))['sha256'])"
        processes = [subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for _ in range(8)]
        results = [(p.wait(), *p.communicate()) for p in processes]
        self.assertEqual([status for status, _, _ in results], [0] * 8, [err for _, _, err in results])
        self.assertEqual(len({out for _, out, _ in results}), 1)
        self.assertEqual([p.name for p in (self.root / "code").iterdir()], [results[0][1].strip()])
        (self.root / "code" / ".abandoned.tmp").mkdir()
        write_json(self.root / "code" / ".abandoned.tmp" / "code.json", {})
        self.assertEqual(dataset_cli.validate(self.root)["code"], 1)

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
