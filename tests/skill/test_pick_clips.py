import importlib.util
import unittest

from helpers import DatasetCase, segs, transcript

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

    def test_normalize_first_leaves_the_second_run_unconverted(self):
        items = pick_clips.select(self.root, self.config(normalize="first"))["items"]
        self.assertIn("Typical disagreement (100%)", items[1]["reason"])
        with self.assertRaises(ValueError):
            pick_clips.select(self.root, self.config(normalize="none"))


if __name__ == "__main__":
    unittest.main()
