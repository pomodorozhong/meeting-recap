"""Run the real sweep wrapper with generated fake model executables."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(shutil.which("zsh"), "requires the wrapper's zsh interpreter")
class SweepOutputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "scratch with spaces"
        binaries = self.root / ".build/release"
        binaries.mkdir(parents=True)
        self.output = self.root / "runs" / "fresh"
        self.log = self.root / "calls.txt"
        self.env = {**os.environ, "AUDIO": str(self.root / "synthetic.wav"), "OUT": str(self.output),
                    "MOCK_CALLS": str(self.log)}
        (binaries / "diarexp").write_text('''#!/bin/zsh
print dia >> "$MOCK_CALLS"
print '[]' > "$2"
''')
        (binaries / "fluidaudiocli").write_text('''#!/bin/zsh
print cli >> "$MOCK_CALLS"
while (( $# )); do
  if [[ "$1" == --output ]]; then
    print '{"segments":[{"speaker":"A","startTimeSeconds":0,"endTimeSeconds":1}]}' > "$2"
    exit 0
  fi
  shift
done
exit 1
''')
        for path in binaries.iterdir():
            path.chmod(0o755)
        shutil.copyfile(ROOT / "experiments/diarization/sortformer_to_segments.py", self.root / "sortformer_to_segments.py")

    def invoke(self):
        return subprocess.run(["zsh", str(ROOT / "experiments/diarization/run_sweep.sh")], cwd=self.root,
                              env=self.env, capture_output=True, text=True, timeout=30)

    def test_fresh_sweep_converts_raw_outputs_and_retry_preserves_them(self):
        run = self.invoke()
        self.assertEqual(run.returncode, 0, run.stderr)
        outputs = sorted((self.output / "other").glob("*_seg.json"))
        self.assertEqual(len(outputs), 5)
        self.assertEqual(json.loads(outputs[0].read_text())[0]["speaker_id"], "A")
        before = {path: path.read_bytes() for path in self.output.rglob("*.json")}
        calls = self.log.read_text()
        retry = self.invoke()
        self.assertEqual(retry.returncode, 2)
        self.assertIn("new writable directory", retry.stderr)
        self.assertEqual(self.log.read_text(), calls)
        self.assertEqual({path: path.read_bytes() for path in self.output.rglob("*.json")}, before)

    def test_existing_empty_directory_is_rejected_before_models_start(self):
        self.output.mkdir(parents=True)
        run = self.invoke()
        self.assertEqual(run.returncode, 2)
        self.assertFalse(self.log.exists())
