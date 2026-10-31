"""The whisper-sortformer pipeline on generated data, with the model stages replaced by fakes."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/pipelines/whisper-sortformer"))

import pipeline  # noqa: E402
import recap  # noqa: E402


def segs(*rows):
    return [{"speaker_id": s, "start_seconds": a, "end_seconds": b} for s, a, b in rows]


def asr(*words):
    return {"segments": [{"text": "".join(w for w, _, _ in words), "start": 0, "end": 10,
                          "words": [{"word": w, "start": a, "end": b} for w, a, b in words]}]}


class Attach(unittest.TestCase):
    def test_words_take_the_overlapping_label_and_join_into_turns(self):
        turns = pipeline.attach(asr(("<|zh|>我", 0.0, 0.3), ("們", 0.3, 0.6), (" deploy", 0.6, 1.0),
                                    ("好", 1.2, 1.5), ("的", 1.5, 1.8)),
                                segs(("S1", 0.0, 1.05), ("S2", 1.1, 2.0)))
        self.assertEqual([(t["speaker_id"], t["text"], t["start_seconds"], t["end_seconds"]) for t in turns],
                         [("S1", "我們 deploy", 0.0, 1.0), ("S2", "好的", 1.2, 1.8)])

    def test_a_long_silence_splits_one_speakers_words(self):
        turns = pipeline.attach(asr(("嗯", 0.0, 0.2), ("對", 3.0, 3.2)), segs(("S1", 0.0, 4.0)))
        self.assertEqual(len(turns), 2)

    def test_words_outside_any_segment_are_unassigned(self):
        turns = pipeline.attach(asr(("嗯", 10.0, 10.2)), segs(("S1", 0.0, 1.0)))
        self.assertEqual(turns[0]["speaker_id"], pipeline.UNASSIGNED)

    def test_zero_length_words_join_a_neighbour(self):
        turns = pipeline.attach(asr(("好", 0.0, 0.2), ("。", 0.2, 0.2), ("呢", 5.0, 5.0), ("你", 5.0, 5.3)),
                                segs(("S1", 0.0, 1.0), ("S2", 4.9, 6.0)))
        self.assertEqual([(t["speaker_id"], t["text"]) for t in turns], [("S1", "好。"), ("S2", "呢你")])

    def test_text_without_word_times_is_refused(self):
        with self.assertRaises(ValueError):
            pipeline.attach({"segments": [{"text": "你好", "start": 0, "end": 1, "words": []}]}, [])

    def test_sortformer_output_becomes_sorted_segments(self):
        raw = {"segments": [{"speaker": "Speaker 1", "startTimeSeconds": 2, "endTimeSeconds": 3},
                            {"speaker": "Speaker 0", "startTimeSeconds": 0, "endTimeSeconds": 1}]}
        self.assertEqual(pipeline.sortformer_segments(raw), segs(("Speaker_0", 0.0, 1.0), ("Speaker_1", 2.0, 3.0)))


class Speakers(unittest.TestCase):
    turns = [{"speaker_id": "S2", "start_seconds": 0, "end_seconds": 1, "text": "我們"},
             {"speaker_id": "S1", "start_seconds": 1.2, "end_seconds": 2, "text": "OK"},
             {"speaker_id": "S3", "start_seconds": 2.5, "end_seconds": 3, "text": "deploy"},
             {"speaker_id": pipeline.UNASSIGNED, "start_seconds": 9, "end_seconds": 9.5, "text": "嗯"}]

    def test_defaults_follow_first_appearance(self):
        self.assertEqual(pipeline.default_speakers(self.turns)["labels"],
                         {"S2": "Speaker A", "S1": "Speaker B", "S3": "Speaker C",
                          pipeline.UNASSIGNED: "Unknown speaker"})

    def test_renaming_and_merging(self):
        labels = {"S2": "Speaker A", "S1": "Host", "S3": "Host", pipeline.UNASSIGNED: "Unknown speaker"}
        named = pipeline.named_turns(self.turns, labels)
        self.assertEqual([(t["speaker"], t["text"]) for t in named],
                         [("Speaker A", "我們"), ("Host", "OK deploy"), ("Unknown speaker", "嗯")])

    def test_a_mapping_must_name_every_label(self):
        with self.assertRaises(ValueError):
            pipeline.check_speakers({"labels": {"S1": "A"}}, self.turns)
        with self.assertRaises(ValueError):
            pipeline.check_speakers({"labels": {"S1": " ", "S2": "A", "S3": "B", pipeline.UNASSIGNED: "?"}},
                                    self.turns)

    def test_markdown_has_timestamps_and_names(self):
        named = pipeline.named_turns(self.turns[:2], {"S2": "Speaker A", "S1": "Speaker B"})
        text = pipeline.transcript_markdown(named, 3725)
        self.assertIn("- Duration: 01:02:05", text)
        self.assertIn("**[00:00:01] Speaker B:** OK", text)


class Summary(unittest.TestCase):
    lines = ["[00:00:05] Speaker A: 我們週五 demo", "[00:01:10] Speaker B: 好，就這樣決定"]

    def test_chunks_never_split_a_line(self):
        parts = pipeline.chunks(["a" * 40] * 5, size=100)
        self.assertEqual([len(p) for p in parts], [2, 2, 1])

    def test_notes_are_parsed_from_a_fenced_reply(self):
        notes = pipeline.parse_notes('好的：\n```json\n{"decisions": [{"text": "週五 demo", '
                                     '"evidence": ["00:01:10"]}], "topics": "bad"}\n```')
        self.assertEqual(notes["decisions"][0]["text"], "週五 demo")
        self.assertEqual(notes["topics"], [])

    def test_a_reply_without_json_is_refused(self):
        with self.assertRaises(ValueError):
            pipeline.parse_notes("沒有")

    def test_evidence_must_start_a_transcript_line(self):
        notes = pipeline.parse_notes(json.dumps({"decisions": [{"text": "x", "evidence": ["00:01:10", "00:09:99"]}],
                                                 "action_items": [{"task": "y", "evidence": []}]}))
        checks = pipeline.check_evidence(notes, self.lines)
        self.assertEqual(checks, {"evidence_dropped": 1, "items_without_evidence": 1})
        text = pipeline.summary_markdown(notes)
        self.assertIn("- x (00:01:10)", text)
        self.assertIn("- y — owner: unknown; due: unknown (no supporting timestamp)", text)
        self.assertIn("## Proposals (not decided)", text)


ASR = asr(("我們", 0.2, 0.6), ("週五", 0.6, 1.0), (" demo", 1.0, 1.4), ("好", 2.0, 2.2), ("的", 2.2, 2.4))
SORTFORMER = {"segments": [{"speaker": "Speaker 0", "startTimeSeconds": 0.0, "endTimeSeconds": 1.5},
                           {"speaker": "Speaker 1", "startTimeSeconds": 1.8, "endTimeSeconds": 2.6}]}
NOTES = {"topics": [{"title": "Demo", "summary": "週五 demo", "evidence": ["00:00:00"]}],
         "decisions": [], "action_items": [], "proposals": [], "open_questions": []}


@unittest.skipUnless(shutil.which("ffmpeg") and Path("/usr/bin/time").exists(), "requires ffmpeg and /usr/bin/time")
class Runs(unittest.TestCase):
    """End-to-end runs with the model processes replaced, checking assembly, failures, and kept outputs."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.audio = self.root / "call.m4a"
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", "sine=f=440:d=3",
                        str(self.audio)], check=True)
        self.out = self.root / "out"
        self.failing = set()

    def tearDown(self):
        self.directory.cleanup()

    def fake_python_stage(self, out, name, script, *args):
        if name in self.failing:
            raise recap.StageError(f"exited with code 1; last lines of logs/{name}.log:\n  boom")
        target = Path(args[1])
        if name == "asr":
            target.write_text(json.dumps({**ASR, "mlx_peak_bytes": 1}))
        else:
            reply = json.dumps(NOTES, ensure_ascii=False)
            target.write_text(json.dumps({"mlx_peak_bytes": 2, "replies": [{"reply": reply}]}))
        return {"wall_seconds": 0.1}

    def fake_diarize(self, out):
        if "diarize" in self.failing:
            raise recap.StageError("Sortformer wrote no output")
        (out / "sortformer.raw.json").write_text(json.dumps(SORTFORMER))
        (out / "diarization.json").write_text(json.dumps(pipeline.sortformer_segments(SORTFORMER)))
        return {}

    def main(self, *argv):
        with mock.patch.object(recap, "python_stage", self.fake_python_stage), \
             mock.patch.object(recap, "diarize", self.fake_diarize), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return recap.main(list(argv))

    def stages(self):
        return json.loads((self.out / "stages.json").read_text())

    def test_a_run_writes_every_artifact(self):
        self.assertEqual(self.main("run", str(self.audio), str(self.out)), 0)
        for name in ("audio.wav", "asr.json", "diarization.json", "turns.json", "speakers.json", "transcript.md",
                     "summary.json", "summary.md", "run.json"):
            self.assertTrue((self.out / name).exists(), name)
        self.assertIn("**[00:00:00] Speaker A:** 我們週五 demo", (self.out / "transcript.md").read_text())
        self.assertIn("**[00:00:02] Speaker B:** 好的", (self.out / "transcript.md").read_text())
        self.assertIn("- **Demo**: 週五 demo (00:00:00)", (self.out / "summary.md").read_text())
        self.assertTrue(all(s["status"] == "completed" for k, s in self.stages().items() if k != "total"))
        self.assertIn("wall_seconds", self.stages()["convert"])
        saved = json.loads((self.out / "summary.json").read_text())
        self.assertEqual(saved["checks"], {"evidence_dropped": 0, "items_without_evidence": 0})
        self.assertEqual(saved["notes"]["topics"][0]["title"], "Demo")
        self.assertFalse(any(p.name.startswith(".") for p in self.out.iterdir()), "partial files left behind")

    def test_an_existing_output_folder_is_refused(self):
        self.out.mkdir()
        (self.out / "keep.txt").write_text("mine")
        self.assertEqual(self.main("run", str(self.audio), str(self.out)), 1)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["keep.txt"])

    def test_output_inside_the_checkout_is_refused(self):
        self.assertEqual(self.main("run", str(self.audio), str(ROOT / "out-test")), 1)
        self.assertFalse((ROOT / "out-test").exists())

    def test_a_failed_stage_keeps_earlier_outputs_and_resumes(self):
        self.failing = {"diarize"}
        self.assertEqual(self.main("run", str(self.audio), str(self.out)), 1)
        stages = self.stages()
        self.assertEqual(stages["diarize"]["status"], "failed")
        self.assertIn("Sortformer wrote no output", stages["diarize"]["error"])
        self.assertTrue((self.out / "asr.json").exists())
        asr_digest = stages["asr"]["outputs"]["asr.json"]

        self.failing = set()
        with mock.patch.object(recap, "convert", side_effect=AssertionError("convert reran")), \
             mock.patch.object(recap, "asr", side_effect=AssertionError("asr reran")):
            self.assertEqual(self.main("run", str(self.audio), str(self.out), "--resume"), 0)
        self.assertEqual(self.stages()["asr"]["outputs"]["asr.json"], asr_digest)
        self.assertEqual(self.stages()["summary"]["status"], "completed")

    def test_a_failed_summary_keeps_the_transcript(self):
        self.failing = {"summary"}
        self.assertEqual(self.main("run", str(self.audio), str(self.out)), 1)
        self.assertTrue((self.out / "transcript.md").exists())
        self.assertFalse((self.out / "summary.md").exists())
        self.assertEqual(self.stages()["summary"]["status"], "failed")

    def test_resume_refuses_a_different_recording(self):
        self.failing = {"asr"}
        self.main("run", str(self.audio), str(self.out))
        other = self.root / "other.wav"
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", "sine=f=220:d=2",
                        str(other)], check=True)
        self.assertEqual(self.main("run", str(other), str(self.out), "--resume"), 1)

    def test_renaming_and_merging_rerender_without_inference(self):
        self.main("run", str(self.audio), str(self.out))
        (self.out / "speakers.json").write_text(json.dumps({"labels": {"Speaker_0": "Host", "Speaker_1": "Host"}}))
        with mock.patch.object(recap, "python_stage", side_effect=AssertionError("inference reran")), \
             contextlib.redirect_stdout(io.StringIO()) as printed:
            self.assertEqual(recap.main(["render", str(self.out)]), 0)
        self.assertIn("summarize --replace", printed.getvalue())
        text = (self.out / "transcript.md").read_text()
        self.assertIn("**[00:00:00] Host:** 我們週五 demo好的", text)
        self.assertNotIn("Speaker A", text)

    def test_summarize_refuses_to_replace_without_asking(self):
        self.main("run", str(self.audio), str(self.out))
        before = (self.out / "summary.md").read_text()
        self.assertEqual(self.main("summarize", str(self.out)), 1)
        self.assertEqual((self.out / "summary.md").read_text(), before)
        self.assertEqual(self.stages()["summary"]["status"], "completed")
        self.assertEqual(self.main("summarize", str(self.out), "--replace"), 0)


if __name__ == "__main__":
    unittest.main()
