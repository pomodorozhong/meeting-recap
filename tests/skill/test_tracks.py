import json
import wave

from helpers import DatasetCase, write_track
from test_cli import run

import evaluate
import review
import tracks

# A speaks, B answers while A is still finishing, a pause, then B alone. A's track also carries
# B's voice 40 dB down, as headphones leak, and a click too short to be speech.
A = [(1, 4), (4.15, 6), (10, 10.05), (12, 13, 80), (16, 18, 80)]
B = [(5.5, 9), (12, 13), (16, 18)]


class Activity(DatasetCase):
    def track(self, name, bursts, seconds=20, **extra):
        return write_track(self.tmp / f"{name}.wav", seconds, bursts, **extra)

    def test_finds_speech_merges_short_gaps_and_ignores_leaks_and_clicks(self):
        spans, duration = tracks.activity(self.track("a", A))
        self.assertEqual(duration, 20)
        self.assertEqual(len(spans), 1)
        self.assertAlmostEqual(spans[0][0], 1, delta=0.03)
        self.assertAlmostEqual(spans[0][1], 6, delta=0.03)

    def test_times_stay_true_when_a_frame_is_not_a_whole_number_of_samples(self):
        # At 7350 Hz a 30 ms frame rounds to 220 samples (29.9 ms); times must count real frames.
        spans, _ = tracks.activity(self.track("odd-rate", [(100, 104)], seconds=110, rate=7350))
        self.assertAlmostEqual(spans[0][0], 100, delta=0.03)
        self.assertAlmostEqual(spans[0][1], 104, delta=0.03)

    def test_silent_track_has_no_speech(self):
        self.assertEqual(tracks.activity(self.track("quiet", [], noise=0))[0], [])

    def test_segments_from_two_tracks(self):
        rows, _ = tracks.track_segments({"A": self.track("a", A), "B": self.track("b", B)})
        self.assertEqual([(r["speaker_id"], round(r["start_seconds"], 1), round(r["end_seconds"], 1)) for r in rows],
                         [("A", 1, 6), ("B", 5.5, 9), ("B", 12, 13), ("B", 16, 18)])

    def test_rejects_bad_tracks(self):
        a, b = self.track("a", A), self.track("b", B)
        cases = {"one track": {"A": a}, "three tracks": {"A": a, "B": b, "C": b},
                 "different lengths": {"A": a, "B": self.track("short", B[:2], seconds=15)},
                 "not a WAV": {"A": a, "B": self.tmp / "a.json"}}
        (self.tmp / "a.json").write_text("{}")
        for name, given in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                tracks.track_segments(given)
        with wave.open(str(self.tmp / "8bit.wav"), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(1)
            handle.setframerate(8000)
            handle.writeframes(bytes(8000))
        with self.assertRaises(ValueError):
            tracks.activity(self.tmp / "8bit.wav")

    def test_parse_tracks(self):
        self.assertEqual(tracks.parse_tracks(["A=mic.wav", "B=system.wav"]), {"A": "mic.wav", "B": "system.wav"})
        for bad in (["mic.wav"], ["=mic.wav"], ["A="], ["A=x.wav", "A=y.wav"]):
            with self.subTest(bad), self.assertRaises(ValueError):
                tracks.parse_tracks(bad)


class TrackReference(DatasetCase):
    def setUp(self):
        super().setUp()
        self.add_recording("rec1", 20)
        self.paths = {"A": write_track(self.tmp / "a.wav", 20, A), "B": write_track(self.tmp / "b.wav", 20, B)}

    def test_builds_clips_and_records_the_tracks(self):
        ref = review.track_reference(self.root, "rec1", self.paths, "tracks1", window=1)
        self.assertEqual([c["speaker_order"] for c in ref["clips"]], [["A", "B"], ["B"], ["B"]])
        self.assertEqual(ref["source"]["kind"], "two_tracks")
        self.assertEqual(set(ref["source"]["tracks"]), {"A", "B"})
        self.assertEqual(ref["source"]["activity"], tracks.SETTINGS)
        rows, _ = tracks.track_segments(self.paths)
        self.add_run("truth", artifacts={"segments": rows})
        result = evaluate.evaluate(self.root, "tracks1", ["truth"], "ev1")["results"][0]
        self.assertEqual(result["clips_correct"], result["clips"])

    def test_rejects_tracks_of_another_recording(self):
        self.add_recording("long", 40)
        with self.assertRaises(ValueError):
            review.track_reference(self.root, "long", self.paths, "tracks2")


class TrackCli(DatasetCase):
    def test_scripts_run_as_the_user_would(self):
        self.add_recording("rec1", 20)
        a, b = write_track(self.tmp / "a.wav", 20, A), write_track(self.tmp / "b.wav", 20, B)
        out = json.loads(run("tracks.py", "--track", f"A={a}", "--track", f"B={b}", "--out", self.tmp / "seg.json").stdout)
        self.assertEqual((out["segments"], out["speech_seconds"]["A"]), (4, 5.0))
        ref = json.loads(run("review.py", "tracks", self.root, "--recording", "rec1", "--track", f"A={a}",
                             "--track", f"B={b}", "--id", "tracks1").stdout)
        self.assertEqual(ref["source"]["kind"], "two_tracks")
        self.assertIn("exactly two tracks", run("tracks.py", "--track", f"A={a}", "--out", self.tmp / "x.json", check=False).stderr)
