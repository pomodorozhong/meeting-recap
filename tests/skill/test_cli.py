"""Run each script as the user would, from its own folder on sys.path."""
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

from helpers import SCRIPTS, segs, write_json, write_wav


def run(script, *args, check=True):
    result = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f"{script} {args} failed: {result.stderr}")
    return result


class Cli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        cls.ds = tmp / "ds"
        run("dataset.py", "init", cls.ds)
        audio = write_wav(tmp / "a.wav", 30)
        run("dataset.py", "add-recording", cls.ds, "--id", "rec1", "--audio", audio, "--duration", 30)
        write_json(tmp / "dia" / "segments.json", segs(("x", 0, 5), ("y", 5, 10), ("z", 10, 11), ("x", 11, 30)))
        write_json(tmp / "dia" / "run.json", {"id": "dia1", "recording_id": "rec1", "model": "m", "status": "completed",
                                              "artifacts": {"segments": "segments.json"}})
        run("dataset.py", "add-run", cls.ds, "--spec", tmp / "dia" / "run.json")
        write_json(tmp / "asr" / "t.json", {"segments": [{"start": 1, "end": 2, "text": "a", "words": [{"word": "a", "start": 1, "end": 2}]}]})
        write_json(tmp / "asr" / "run.json", {"id": "asr1", "recording_id": "rec1", "model": "m", "status": "completed",
                                              "artifacts": {"transcript": "t.json"}})
        run("dataset.py", "add-run", cls.ds, "--spec", tmp / "asr" / "run.json")
        cls.tmp = tmp

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_every_script_has_help(self):
        for script in sorted(p.name for p in SCRIPTS.glob("*.py") if p.name not in {"common.py", "scoring.py"}):
            with self.subTest(script):
                self.assertIn("usage", run(script, "--help").stdout)

    def test_errors_exit_nonzero_with_one_line(self):
        result = run("dataset.py", "validate", self.tmp, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)

    def test_full_flow(self):
        out = json.loads(run("attach.py", self.ds, "--asr-run", "asr1", "--diarization-run", "dia1", "--id", "att1").stdout)
        self.assertEqual(out["parents"], ["asr1", "dia1"])
        config = write_json(self.tmp / "pick.json", {"id": "s1", "question": "Who?", "seed": 3, "recordings": [
            {"recording_id": "rec1", "diarization_run": "dia1", "speaker_clips": 2}]})
        run("pick_clips.py", self.ds, "--config", config, "--out", self.tmp / "plan.json")
        self.assertEqual(json.loads(run("review.py", "prepare", self.ds, "--plan", self.tmp / "plan.json").stdout)["id"], "s1")
        answer = write_json(self.tmp / "answer.json", {"item_id": "c01", "state": "confirmed", "annotation": {"speaker_order": ["A", "B"]}})
        run("review.py", "answer", self.ds, "--session", "s1", "--file", answer)
        run("review.py", "close", self.ds, "--session", "s1")
        run("review.py", "reference", self.ds, "--session", "s1", "--id", "ref1")
        out = json.loads(run("evaluate.py", self.ds, "--reference", "ref1", "--runs", "dia1", "--id", "ev1").stdout)
        self.assertEqual(out["results"][0]["run_id"], "dia1")
        truth = write_json(self.tmp / "truth.json", [{"speaker_id": "A", "start_seconds": 0, "end_seconds": 5}])
        run("review.py", "known", self.ds, "--recording", "rec1", "--segments", truth, "--id", "known1")
        counts = json.loads(run("dataset.py", "validate", self.ds).stdout)
        self.assertEqual(counts, {"recordings": 1, "runs": 3, "sessions": 1, "references": 2, "code": 1})

    def test_review_server_starts_as_a_script(self):
        plan = write_json(self.tmp / "serve-plan.json", {
            "id": "serve", "question": "Who?", "selector": {"name": "agent-selected", "version": "1"},
            "items": [{"id": "c1", "task": "speaker_order", "recording_id": "rec1", "start_seconds": 0,
                       "end_seconds": 5, "reason": "test", "run_ids": ["dia1"]}]})
        run("review.py", "prepare", self.ds, "--plan", plan)
        process = subprocess.Popen([sys.executable, str(SCRIPTS / "review.py"), "serve", str(self.ds), "--session", "serve"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            url = process.stdout.readline().split(": ", 1)[1].strip()
            with urllib.request.urlopen(url, timeout=5) as response:
                self.assertEqual(response.status, 200)
        finally:
            process.kill()
            _, stderr = process.communicate(timeout=5)
        self.assertNotIn("Traceback", stderr)


if __name__ == "__main__":
    unittest.main()
