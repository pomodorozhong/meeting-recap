"""Exercise the patch's actual export/finalization functions without models or the GUI app."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SWIFT_CACHE = Path(tempfile.gettempdir()) / "meeting-recap-swift-module-cache"


def patched_function(name):
    patch = (ROOT / "experiments/hushscribe-harness/hushscribe-trial-harness.patch").read_text()
    source = "\n".join(line[1:] for line in patch.splitlines() if line.startswith(("+", " "))
                       and not line.startswith("+++"))
    start = source.index(f"    private func {name}(")
    brace = source.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("swift"), "requires macOS and Swift")
class TrialExports(unittest.TestCase):
    def run_trial(self, output_blocked=False, result_blocked=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, result = root / "output", root / "result.json"
            if output_blocked:
                output.write_text("generated blocker")
            if result_blocked:
                result.mkdir()
            script = root / "probe.swift"
            script.write_text('''import Foundation
struct Engine { var lastError: String? = nil }
struct Store { var utterances = [1] }
struct Application { func terminate(_ sender: Any?) { exit(0) } }
let NSApp = Application()
let transcriptionEngine = Engine()
let transcriptStore = Store()
let automatedTrialStartedAt: Date? = nil
let automatedTrialFileSessionStartedAt: Date? = nil
let automatedTrialTranscriptionFinishedAt: Date? = nil
let automatedTrialDiarizationSucceeded: Bool? = true
let automatedTrialDiarizationSegmentCount: Int? = 1
let automatedTrialDiarizationSpeakerCount: Int? = 1
var automatedTrialExportError: String? = nil
func diagLog(_ message: String) {}
''' + patched_function("writeAutomatedDiarization") + "\n" + patched_function("finishAutomatedTrial") + '''
do { try writeAutomatedDiarization([(speakerId: "A", startTime: 0, endTime: 1)]) }
catch { automatedTrialExportError = error.localizedDescription }
finishAutomatedTrial(savedPath: URL(fileURLWithPath: "/synthetic-transcript.md"))
''')
            env = {**os.environ, "HUSHSCRIBE_TRIAL_OUTPUT": str(output), "HUSHSCRIBE_TRIAL_RESULT": str(result)}
            run = subprocess.run(["swift", "-module-cache-path", str(SWIFT_CACHE), str(script)],
                                 env=env, capture_output=True, text=True, timeout=120)
            data = json.loads(result.read_text()) if result.is_file() else None
            artifact = json.loads((output / "diarization.json").read_text()) if (output / "diarization.json").is_file() else None
            return run, data, artifact

    def test_success_requires_saved_diarization_and_result(self):
        run, result, artifact = self.run_trial()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(artifact[0]["speaker_id"], "A")

    def test_export_failure_is_a_failed_trial(self):
        run, result, artifact = self.run_trial(output_blocked=True)
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["error"])
        self.assertIsNone(artifact)

    def test_result_write_failure_returns_nonzero(self):
        run, result, artifact = self.run_trial(result_blocked=True)
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn("trial result could not be saved", run.stderr)
        self.assertIsNone(result)
        self.assertIsNotNone(artifact)
