"""Verify historical synthetic score replay and refusal of changed evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments/synthetic-call"))
import action_bench
import replay_actions


class Replay(unittest.TestCase):
    def test_all_seventy_cells_match_published_results(self):
        result = replay_actions.replay()
        self.assertEqual(sum(len(modes) for modes in result["cases"].values()), 70)
        self.assertEqual(result["micro"]["large-focused"]["strict_hits"], 7)
        self.assertEqual(result["micro"]["audio-focused"]["strict_hits"], 4)

    def changed_bundle(self, change):
        bundle = json.loads(replay_actions.BUNDLE.read_text())
        change(bundle)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bundle.json"
            path.write_text(json.dumps(bundle))
            return replay_actions.replay(path)

    def test_refuses_missing_or_unexpected_files(self):
        def missing(bundle):
            bundle["files"].pop(next(iter(bundle["files"])))
        def traversal(bundle):
            bundle["files"]["../outside.json"] = {"text": "{}", "sha256": ""}
        for change in (missing, traversal):
            with self.subTest(change=change.__name__), self.assertRaisesRegex(ValueError, "unexpected replay files"):
                self.changed_bundle(change)

    def test_refuses_changed_bytes_even_with_unchanged_json_values(self):
        def change(bundle):
            bundle["files"]["archive/audio-focused/items.json"]["text"] += "\n"
        with self.assertRaisesRegex(ValueError, "changed replay file"):
            self.changed_bundle(change)

    def test_changed_prediction_cannot_reuse_original_verdicts(self):
        def change(bundle):
            entry = bundle["files"]["archive/audio-focused/items.json"]
            entry["text"] = "[]\n"
            entry["sha256"] = hashlib.sha256(entry["text"].encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "changed benchmark output"):
            self.changed_bundle(change)

    def test_missing_model_preflight_leaves_no_partial_benchmark(self):
        def fake_run(argv, **kwargs):
            if "preflight" in argv:
                self.assertEqual(argv[-2:], ["--asr", "all"])
                raise subprocess.CalledProcessError(1, argv)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new-results"
            with mock.patch.object(action_bench.subprocess, "run", side_effect=fake_run), \
                    mock.patch.object(action_bench, "run_case") as run:
                with self.assertRaises(subprocess.CalledProcessError):
                    action_bench.main([str(output)])
                run.assert_not_called()
                self.assertFalse(output.exists())
