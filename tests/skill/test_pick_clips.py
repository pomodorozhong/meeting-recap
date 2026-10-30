import importlib.util
import unittest

from helpers import DatasetCase, segs, transcript, write_json

import pick_clips

HAS_OPENCC = importlib.util.find_spec("opencc") is not None


def alternating(duration=240, rare=(60, 61)):
    rows, t, speakers = [], 0, ["A", "B"]
    while t < duration:
        end = min(t + 5, duration)
        if t <= rare[0] < end:
            parts = [(speakers[0], t, rare[0]), ("C", *rare), (speakers[0], rare[1], end)]
            rows += [p for p in parts if p[2] > p[1]]
        else:
            rows.append((speakers[0], t, end))
        speakers.reverse()
        t = end
    return segs(*rows)


def words(text, duration=120, special=None):
    special = special or {}
    return transcript(*[(special.get(i // 15, text), i, i + 1) for i in range(duration)])


class PickClips(DatasetCase):
    def setUp(self):
        super().setUp()
        self.add_recording("rec1", 240)
        self.add_run("dia1", artifacts={"segments": alternating()})

    def config(self, **extra):
        rec = {"recording_id": "rec1", "diarization_run": "dia1", "speaker_clips": 4,
               "speaker_show_runs": ["dia1"], **extra.pop("rec", {})}
        return {"id": "s1", "question": "Who speaks?", "seed": 7, "recordings": [rec], **extra}

    def test_refuses_a_run_changed_after_registration(self):
        write_json(self.root / "runs" / "dia1" / "segments.json", alternating(rare=(100, 101)))
        with self.assertRaises(ValueError):
            pick_clips.select(self.root, self.config())

    def test_speaker_clips_are_seeded_binned_and_include_the_rarest_label(self):
        plan = pick_clips.select(self.root, self.config())
        self.assertEqual(plan, pick_clips.select(self.root, self.config()))
        items = plan["items"]
        self.assertEqual(len(items), 4)
        self.assertEqual([i["id"] for i in items], ["c01", "c02", "c03", "c04"])
        rare = [i for i in items if i["reason"].startswith("Rarest diarization label")]
        self.assertEqual(len(rare), 1)
        self.assertTrue(rare[0]["start_seconds"] <= 60 and rare[0]["end_seconds"] >= 61)
        for item in items:
            self.assertEqual(item["end_seconds"] - item["start_seconds"], 15)
            self.assertEqual((item["padding_seconds"], item["run_ids"]), (1, ["dia1"]))
        self.assertEqual(plan["selector"]["seed"], 7)
        self.assertEqual(plan["selector"]["method"]["window_seconds"], 15)

    def test_skip_before_and_window_options(self):
        plan = pick_clips.select(self.root, self.config(rec={"skip_before": 70}, window_seconds=10))
        self.assertTrue(all(i["start_seconds"] >= 70 for i in plan["items"]))
        self.assertTrue(all(i["end_seconds"] - i["start_seconds"] == 10 for i in plan["items"]))

    def test_fills_a_bin_crowded_by_the_rare_clip_without_overlap(self):
        # In 120 s with 4 clips, every candidate in one bin is within 20 s of the rare-label clip.
        self.add_recording("short", 120)
        self.add_run("dia-short", recording_id="short", artifacts={"segments": alternating(120)})
        plan = pick_clips.select(self.root, self.config(rec={"recording_id": "short", "diarization_run": "dia-short"}))
        starts = sorted(i["start_seconds"] for i in plan["items"])
        self.assertEqual((len(starts), plan["selector"]["shortfall"]), (4, []))
        self.assertTrue(all(b - a >= 15 for a, b in zip(starts, starts[1:])), starts)

    def test_reports_bins_with_no_candidates(self):
        self.add_recording("quiet", 240)
        self.add_run("dia-quiet", recording_id="quiet", artifacts={"segments": alternating(60, rare=(30, 31))})
        plan = pick_clips.select(self.root, self.config(rec={"recording_id": "quiet", "diarization_run": "dia-quiet"}))
        self.assertEqual(len(plan["items"]) + len(plan["selector"]["shortfall"]), 4)
        self.assertTrue(plan["selector"]["shortfall"])
        self.assertTrue(all(s["bin_seconds"][0] >= 60 for s in plan["selector"]["shortfall"]))

    def test_a_single_clip_is_the_rare_one(self):
        items = pick_clips.select(self.root, self.config(rec={"speaker_clips": 1}))["items"]
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["reason"].startswith("Rarest diarization label"))

    def test_rejects_unfinished_or_mismatched_runs(self):
        self.add_recording("rec2", 240)
        self.add_run("dia2", recording_id="rec2", artifacts={"segments": alternating()})
        self.add_run("dia3", artifacts={"segments": alternating()}, status="failed")
        for run_id in ["dia2", "dia3"]:
            with self.subTest(run_id), self.assertRaises(ValueError):
                pick_clips.select(self.root, self.config(rec={"diarization_run": run_id}))


@unittest.skipUnless(HAS_OPENCC, "transcript selection needs opencc-python-reimplemented")
class PickTranscriptClips(DatasetCase):
    def setUp(self):
        super().setUp()
        self.add_recording("rec1", 120)
        # Traditional vs. Simplified everywhere, and different words in the 30–45 s window.
        self.add_run("asr1", artifacts={"transcript": words("們們")})
        self.add_run("asr2", artifacts={"transcript": words("们们", special={2: "天地"})})

    def config(self, **extra):
        rec = {"recording_id": "rec1", "transcript_runs": ["asr1", "asr2"], "transcript_clips": 1}
        return {"id": "s1", "question": "Which words?", "seed": 1, "recordings": [rec], **extra}

    def test_picks_the_biggest_disagreement_and_the_median(self):
        items = pick_clips.select(self.root, self.config())["items"]
        self.assertEqual([(i["start_seconds"], i["task"]) for i in items[:1]], [(30.0, "transcript")])
        self.assertEqual(len(items), 2)
        self.assertIn("Typical disagreement (0%)", items[1]["reason"])
        self.assertEqual(items[0]["run_ids"], ["asr1", "asr2"])

    def test_reports_missing_transcript_clips(self):
        plan = pick_clips.select(self.root, self.config(recordings=[
            {"recording_id": "rec1", "transcript_runs": ["asr1", "asr2"], "transcript_clips": 5}]))
        # Windows start every 15 s up to 105 s; only 105 s is more than 60 s from the top pick at 30 s,
        # and no window is left for the typical clip.
        self.assertEqual([s["missing"] for s in plan["selector"]["shortfall"]], [3, 1])
        self.assertEqual([i["start_seconds"] for i in plan["items"]], [30.0, 105.0])

    def speech(self, recording_id, duration, start, end):
        self.add_recording(recording_id, duration)
        for run_id, text in ((f"{recording_id}-a", "們們"), (f"{recording_id}-b", "们们")):
            self.add_run(run_id, recording_id=recording_id,
                         artifacts={"transcript": transcript(*[(text, i, i + 1) for i in range(start, end)])})
        rec = {"recording_id": recording_id, "transcript_runs": [f"{recording_id}-a", f"{recording_id}-b"],
               "transcript_clips": 1}
        return self.config(recordings=[rec])

    def test_the_typical_clip_is_never_a_repeat(self):
        plan = pick_clips.select(self.root, self.speech("one", 120, 90, 105))
        self.assertEqual([(i["start_seconds"], i["end_seconds"]) for i in plan["items"]], [(90.0, 105.0)])
        self.assertEqual([s["missing"] for s in plan["selector"]["shortfall"]], [1])

    def test_the_last_full_window_is_a_candidate(self):
        cases = {"ends at the recording's end": (120, 105, 120, 105), "exactly one window": (15, 0, 15, 0),
                 "fractional duration": (22.5, 0, 22, 0)}
        for name, (duration, start, end, skip) in cases.items():
            with self.subTest(name):
                config = self.speech(name.replace(" ", "-").replace("'", ""), duration, start, end)
                config["recordings"][0]["skip_before"] = skip
                plan = pick_clips.select(self.root, config)
                self.assertEqual([(i["start_seconds"], i["end_seconds"]) for i in plan["items"]], [(float(skip), skip + 15.0)])

    def test_rejects_unknown_config_keys(self):
        with self.assertRaises(ValueError):
            pick_clips.select(self.root, self.config(normalize="first"))


if __name__ == "__main__":
    unittest.main()
