"""Exercise the shell-to-review-skill path with a broken system python3 on PATH."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "experiments/synthetic-call"


class ComparisonInterpreter(unittest.TestCase):
    def test_skill_subprocesses_use_locked_python_even_with_unusable_system_python(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "checkout"
            project = repo / "experiments/synthetic-call"
            project.mkdir(parents=True)
            for name in ("compare_fast.sh", "turn_order.py", "pyproject.toml", "uv.lock"):
                shutil.copy2(HERE / name, project / name)
            (project / ".venv").symlink_to(Path(sys.prefix), target_is_directory=True)
            skill = ".agents/skills/meeting-experiment-review"
            shutil.copytree(ROOT / skill, repo / skill, ignore=shutil.ignore_patterns("__pycache__"))
            # Replace inference and the unrelated final scorer; keep turn_order and every skill CLI real.
            (project / "score_case.py").write_text("print('{}')\n")
            mlx = repo / "experiments/mlx"
            (mlx / ".venv/bin").mkdir(parents=True)
            (mlx / ".venv/bin/python").symlink_to(sys.executable)
            (mlx / "run.py").write_text("from pathlib import Path\nimport sys\nPath(sys.argv[2]).write_text('{}')\n")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            trap = bin_dir / "python3"
            trap.write_text("#!/bin/sh\necho system-python-was-used >&2\nexit 93\n")
            trap.chmod(0o755)
            source = root / "source"
            source.mkdir()
            with wave.open(str(source / "call.wav"), "wb") as wav:
                wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                wav.writeframes(b"\x10\x00" * 32000)
            digest = hashlib.sha256((source / "call.wav").read_bytes()).hexdigest()
            segments = [{"speaker_id": "A", "start_seconds": 0.0, "end_seconds": 2.0}]
            asr = {"segments": [{"text": "測試", "start": 0.0, "end": 2.0,
                                 "words": [{"word": "測試", "start": 0.0, "end": 2.0}]}]}
            out = root / "probe"
            (out / "pipeline").mkdir(parents=True)
            shutil.copy2(source / "call.wav", out / "pipeline/audio.wav")
            for path, data in {
                source / "manifest.json": {"call_sha256": digest, "duration_seconds": 2.0},
                source / "segments.json": segments,
                out / "scores.json": {},
                out / "who.json": {"segments": segments, "model_revision": "fixture"},
                out / "breeze.json": {**asr, "model_revision": "fixture"},
                out / "pipeline/asr.json": asr,
                out / "pipeline/diarization.json": segments,
                out / "pipeline/run.json": {"models": {"asr": "fixture", "diarization_weights_sha256": "fixture"}},
            }.items():
                path.write_text(json.dumps(data))
            (out / "input.sha256").write_text(digest)
            env = {**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]}
            result = subprocess.run([project / "compare_fast.sh", source, out], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((out / "extension/turn-order.json").read_text())
            self.assertEqual(report["errors"], {})
            self.assertEqual(len(report["results"]), 14)
            self.assertTrue(all(row["turns_recovered"] == 1 for row in report["results"].values()))
