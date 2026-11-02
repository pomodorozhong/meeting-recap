"""Keep EmotiVoice metadata offline and clean up failed child renders."""
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parents[2] / "experiments/synthetic-call"
sys.path.insert(0, str(HERE))
import emoti_voice as emoti
import generate


class EmotiVoiceMetadata(unittest.TestCase):
    def test_import_and_provenance_do_not_initialize_inference_libraries(self):
        program = """
import sys
sys.path.insert(0, sys.argv[1])
import emoti_voice
import generate
pin = emoti_voice.provenance('emotivoice-1093')
assert pin['speaker_id'] == '1093'
assert len(pin['uv_lock_sha256']) == 64
assert not {'torch', 'transformers', 'mlx', 'numpy', 'huggingface_hub'} & sys.modules.keys()
"""
        subprocess.run([sys.executable, "-I", "-c", program, str(HERE)], check=True)

    def test_emoti_only_cast_does_not_request_qwen_or_f5(self):
        config = generate.voice_configuration({"A": {"voice": "emotivoice-1093"}})
        self.assertEqual(set(config["model"]), {
            "FPVG/EmotiVoice-pretrained-models", "WangZeJun/simbert-base-chinese"})
        self.assertEqual(set(config["voice_config"]), {"emotivoice-1093"})
        self.assertEqual(config["voice_config"]["emotivoice-1093"]["speaker_id"], "1093")

    def test_mixed_cast_retains_each_engine_and_speaker_provenance(self):
        config = generate.voice_configuration({
            "A": {"voice": "f5-news-female"},
            "B": {"voice": "dylan"},
            "C": {"voice": "emotivoice-1066"},
        })
        self.assertEqual(set(config["model"]), {
            generate.MODEL[0], "lucasnewman/f5-tts-mlx", "lucasnewman/vocos-mel-24khz",
            "FPVG/EmotiVoice-pretrained-models", "WangZeJun/simbert-base-chinese"})
        self.assertEqual(set(config["voice_config"]), {"f5-news-female", "emotivoice-1066"})
        self.assertEqual(config["voice_config"]["f5-news-female"]["reference"]["sha256"],
                         "bb712833cd31d8df805cd29eee112a7db70dbf08ab51e4e2ec7b8106752d97ec")
        self.assertEqual(config["voice_config"]["emotivoice-1066"]["speaker_id"], "1066")


class EmotiChildRendering(unittest.TestCase):
    def test_existing_cast_skips_the_child_process(self):
        speakers = {"A": {"voice": "f5-news-female"}, "B": {"voice": "dylan"}}
        turns = [{"speaker": "A", "text": "第一句。"}, {"speaker": "B", "text": "第二句。"}]
        with mock.patch.object(emoti.subprocess, "run") as child:
            with emoti.render_turns(turns, speakers, 7) as clips:
                self.assertEqual(clips, {})
        child.assert_not_called()

    def test_partial_child_output_is_rejected_and_removed(self):
        temporary_roots = []

        def partial(argv, **kwargs):
            output = Path(argv[-1])
            temporary_roots.append(output.parent)
            output.mkdir()
            (output / "000.wav").write_bytes(b"partial")

        speakers = {"A": {"voice": "emotivoice-1012"}}
        turns = [{"speaker": "A", "text": "第一句。"}, {"speaker": "A", "text": "第二句。"}]
        with mock.patch.object(emoti.subprocess, "run", side_effect=partial):
            with self.assertRaisesRegex(ValueError, "every requested turn"):
                with emoti.render_turns(turns, speakers, 7):
                    self.fail("partial rendering must not yield clips")
        self.assertEqual(len(temporary_roots), 1)
        self.assertFalse(temporary_roots[0].exists())

    def test_failed_child_preserves_its_error_and_removes_temporary_audio(self):
        temporary_roots = []

        def fail(argv, **kwargs):
            output = Path(argv[-1])
            temporary_roots.append(output.parent)
            output.mkdir()
            (output / "000.wav").write_bytes(b"interrupted")
            raise subprocess.CalledProcessError(9, argv)

        with mock.patch.object(emoti.subprocess, "run", side_effect=fail):
            with self.assertRaises(subprocess.CalledProcessError) as failure:
                with emoti.render_turns([{"speaker": "A", "text": "第一句。"}],
                                        {"A": {"voice": "emotivoice-1066"}}, 7):
                    self.fail("failed child must not yield clips")
        self.assertEqual(failure.exception.returncode, 9)
        self.assertEqual(len(temporary_roots), 1)
        self.assertFalse(temporary_roots[0].exists())

    def test_native_audio_is_removed_when_later_generation_raises(self):
        temporary_roots = []

        def complete(argv, **kwargs):
            output = Path(argv[-1])
            temporary_roots.append(output.parent)
            output.mkdir()
            (output / "000.wav").write_bytes(b"generated audio")

        with mock.patch.object(emoti.subprocess, "run", side_effect=complete):
            with self.assertRaisesRegex(RuntimeError, "later synthesis failed"):
                with emoti.render_turns([{"speaker": "A", "text": "第一句。"}],
                                        {"A": {"voice": "emotivoice-1093"}}, 7) as clips:
                    self.assertTrue(clips[0].is_file())
                    raise RuntimeError("later synthesis failed")
        self.assertEqual(len(temporary_roots), 1)
        self.assertFalse(temporary_roots[0].exists())
