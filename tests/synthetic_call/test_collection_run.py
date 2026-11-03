"""Exercise the comparison's entry point without running any model."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
import collection_weights as weights  # noqa: E402


def run(*args):
    return subprocess.run([HERE / "collection_run.sh", *args], capture_output=True, text=True)


class EntryPoint(unittest.TestCase):
    def test_plan_lists_every_step_without_touching_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "results"
            done = run(tmp, str(target), "--plan")
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stdout.split(), ["decode", "recaps", "diarize", "split", "turns", "replays",
                                                   "scores"])
            self.assertFalse(target.exists())

    def test_refuses_unusable_arguments_before_any_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            for args, message in (((tmp,), "usage"), ((tmp, "relative"), "absolute"),
                                  ((tmp + "/none", tmp + "/new"), "no fixtures"), ((tmp, tmp), "already exists"),
                                  ((tmp, tmp + "/new", "--step", "other"), "unknown step"),
                                  ((tmp, tmp + "/new", "--other"), "usage")):
                done = run(*args)
                self.assertEqual(done.returncode, 2, args)
                self.assertIn(message, done.stderr)
                self.assertEqual(done.stdout, "")


class Weights(unittest.TestCase):
    def test_digest_matches_the_pipeline_format_and_check_refuses_a_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "ls-eend"
            (folder / "sub").mkdir(parents=True)
            (folder / "sub/a.bin").write_bytes(b"a")
            first = weights.tree_sha256(folder)
            (folder / "sub/a.bin").write_bytes(b"b")
            self.assertNotEqual(first, weights.tree_sha256(folder))
            with self.assertRaises(ValueError):
                weights.check("ls-eend", root)

    def test_pins_match_the_digests_the_runner_requires(self):
        import ast
        tree = ast.parse((HERE / "collection_followup.py").read_text())
        required = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                        and n.targets[0].id == "ALT_DIGESTS")
        self.assertEqual(required, {k: v["tree_sha256"] for k, v in weights.SOURCES.items()})


if __name__ == "__main__":
    unittest.main()
