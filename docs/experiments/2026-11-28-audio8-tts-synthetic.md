# 2026-11-28: Audio8-TTS-Realistic-0.6B as a voice for the synthetic collection

**Status:** complete

**Outcome:** Promising, not adopted yet. Audio8 copies the collection's voices, so same-gender speakers stay distinct, and the project owner judged it the most natural voice tried so far. But it failed the collection's English-word gate on the handoff call with three seeds, and the failure is in one voice: its copy of the F5 female voice never said `timeout` clearly enough for Whisper to hear it, while its copy of a male voice said the same word cleanly. The collection keeps its F5, Qwen and EmotiVoice voices ([decisions 8 and 9](../decisions.md)) for now, and [#99](https://github.com/pomodorozhong/meeting-recap/issues/99) tests voices that Audio8 makes from seeds instead of copies.

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `uv sync --locked --project experiments/synthetic-call`; the first run downloads the pinned model |
| Voice the fourteen scripts | `uv run --locked --project experiments/synthetic-call python experiments/synthetic-call/generate_audio8.py "$OUT" --simplified` |
| Run the English-word gate | `uv run --locked --project experiments/synthetic-call python experiments/synthetic-call/check_voice.py "$OUT/handoff"` |

- **It needs:** nothing beyond the repository and the network for the first download.
- **It writes:** `OUT/<call>/` in the [collection's layout](../../experiments/synthetic-call/README.md#what-it-makes), plus `audio8-report.json` per call, `OUT/references/` with the cloning references, and `voice-check.json` from the gate.
- **Takes about:** 30 minutes for all fourteen calls on the M2 Pro, including the references, plus the first download (about 4.8 GB).
- **By hand:** listening, for example on the [comparison page](../../experiments/synthetic-call/README.md#listen-to-voices-side-by-side).
- **Expect to differ:** timings. Two runs of `handoff` on the same machine gave the same WAV bytes.

## Question

Would Audio8-TTS-Realistic-0.6B be a better voice for the synthetic collection than the voices it uses?

- **Decision it informs:** whether to rebuild the collection with Audio8, or keep the voices in decisions 8 and 9.
- **Expected result:** none was written down before the runs. As with [the LFM3 test](2026-11-27-lfm3-tts-synthetic.md), this summary reports what was observed rather than testing a registered rule. [#95](https://github.com/pomodorozhong/meeting-recap/issues/95) set the order of checks: voices first, then the gate, then a listen.
- **Builds on:** the [English-word gate](../../experiments/synthetic-call/README.md#voices-and-the-english-word-gate) that picked the F5 voice, and the LFM3 test, which failed partly for having one voice per gender.

## Plan

- **Input:** the fourteen scripts of the 17-recording collection, unchanged: eight in Mandarin with English terms, six in English, one to four speakers.
- **Voices:** Audio8 has a single default voice and zero-shot cloning from a reference clip and its exact transcript, in 23 languages. So it has as many voices as there are references. Each old voice is cloned from one fixed sentence spoken by that voice's own engine (Qwen CustomVoice or EmotiVoice), one per voice and language, with seed 7; the F5 voice is cloned from its pinned reference clip, the one F5 itself clones from. Same-gender speakers in a call keep distinct voices because their references differ, which LFM3 could not offer.
- **Method:** [`generate_audio8.py`](../../experiments/synthetic-call/generate_audio8.py) voices every turn with [Audio8-TTS-Realistic-0.6b MLX bf16](https://huggingface.co/mlx-community/Audio8-TTS-Realistic-0.6b-bf16) `f2addfde` through the collection's locked mlx-audio 0.6.1, then levels, times and mixes the turns exactly as `generate.py` does. Only the voices change. Sampling uses the model card's settings (temperature 0.7, top-p 0.9, top-k 50) with up to 1,024 frames a turn, seeded with seed 7 plus the turn index ([`audio8-voice.json`](../../experiments/synthetic-call/reference/audio8-voice.json)).
- **Checks:** the English-word gate on `handoff`, and an informal listen by the project owner. No structured listening review and no transcript scoring against the collection.

### Changes to the plan

No plan was committed before the runs. Three checks were added after the first gate result:

- **Simplified characters.** The scripts are in Traditional characters, and the F5 voice converts them to Simplified (OpenCC t2s) before speaking. Spoken from Traditional text, Audio8's Mandarin was garbled (Whisper heard 多是机器极为让使用者等杠酒 for 多試幾次只會讓使用者等更久). The generator's `--simplified` option applies the same conversion as F5, and every later run, including the fourteen calls, used it.
- **Seeds 8 and 9** on `handoff`, to tell whether the missed `timeout` was one unlucky sample.
- **Each `timeout` line on its own.** After the project owner's listen, `handoff`'s two lines with `timeout` were decoded one turn file at a time, with the gate's Whisper model and settings (Mandarin declared, temperature 0, no conditioning on earlier text), for every version: turn 1, spoken by the copy of Qwen's `dylan` (male), and turn 10, by the copy of the F5 voice (female). The gate itself checks only the female speaker's turns, because it was built to choose the female voice. This was a one-off check, not a script in the repository.

## Results

| Check on `handoff` | Audio8, script text | Audio8, Simplified, seeds 7 / 8 / 9 | F5 female voice (the collection's) |
| --- | --- | --- | --- |
| Gate: standalone `log` recovered | Yes | Yes / Yes / Yes | Yes |
| Gate: standalone `timeout` recovered | No ("TWIMDO") | No ("Kineodo" / "TimeMode" / "TiMidu") | Yes |
| Gate: Mandarin character agreement on the three checked turns | 75.8% | 100% / 100% / 100% | 97.9% |
| Gate verdict | **Fail** | **Fail** on every seed | Pass |

| `timeout` heard, each line decoded alone | Turn 1, male: "…測試的 timeout 還有出現嗎？" | Turn 10, female: "等一下，timeout 的原因…" |
| --- | --- | --- |
| Current collection | Yes ("Time Out") | Yes ("Time Out") |
| LFM3 | No ("太阳毛", and the Mandarin around it garbled) | No ("Time Palm") |
| Audio8, Simplified, seed 7 | Yes ("Timeout") | No ("KaiNyodo") |
| Audio8, Simplified, seed 8 | Yes ("Timeout") | No ("Time Mode") |
| Audio8, Simplified, seed 9 | No ("Tile") | No ("胎密度") |

- **Voices:** passed the check that ruled out LFM3. Eleven references were needed for the fourteen calls (seven voices, most in both languages), plus F5's own clip.
- **The gate:** with Simplified text Audio8's Mandarin was flawless, better than F5's, but the copy of the female voice mispronounced the English word `timeout` inside a Mandarin sentence on all three seeds. `log`, said by the same voice, was always heard. The gate requires both, because the collection exists to test English terms in Mandarin speech.
- **Generation:** all fourteen calls, 35.9 minutes of audio, generated in 26.8 minutes; no turn reached the frame limit.
- **The failure is in one copied voice.** The copy of the male voice said `timeout` as one clean word on two of three seeds, closer than the collection's own "Time Out", with the rest of the line word-perfect. So Audio8 can say the word; its copy of the F5 voice can't. That voice is copied from F5's own reference, a few seconds of a Mandarin news reading with no English in it, which is a likely cause but was not tested.
- **Listening:** the project owner compared the fourteen calls with the collection's versions on the comparison page and judged Audio8 the most natural voice tried so far, with one exception: turn 10 of `handoff` sounded wrong. This was an informal listen, not blind and not a structured review.

**Limits.** One gate call, three seeds, two lines checked one at a time, and one informal listen. The gate covers English terms in Mandarin speech, in the female voice only, so the other copied voices were checked on English terms only by ear. The references are a single sentence spoken by another synthetic voice, so the clones are copies of copies; longer or natural references, other sampling settings and the upstream PyTorch model were not tried.

## Runtime and memory

Measured by the generator on the M2 Pro: 35.9 minutes of audio in 26.8 minutes of wall time (about 0.75× real time), model loaded once for all calls; peak MLX memory 7.18–9.15 GB per call, against LFM3's 4.1–4.3 GB. Rendering the eleven references with Qwen and EmotiVoice and loading the models added about 3 minutes, before the first turn.

## Decision

Keep the collection's voices for now, and test voices that Audio8 makes itself ([decision 21](../decisions.md)). Audio8 is the most natural voice tried, solves LFM3's voice problem by copying, and with Simplified text its Mandarin is excellent. But one of its copies failed the gate that picked the F5 voice on every seed tried, on the one thing the gate checks for, and copying ties every voice to the old engines and their flaws. [#99](https://github.com/pomodorozhong/meeting-recap/issues/99) asks whether Audio8's own voice changes with the seed, so that each speaker can get a seed-made voice from one model, with every voice gated on an English term. Rebuilding the collection with Audio8 would be its own decision, since every published result uses the current audio. The generator stays, so Audio8 voices can be made on the same scripts with one command.

## Where this ran

- **Code:** the generator at the commit that adds this summary, on `feat/audio8-tts`, not yet on `main`.
- **Models and weights:** `mlx-community/Audio8-TTS-Realistic-0.6b-bf16` at `f2addfde1a6196399bf23330dfd66c47b2fe10ea`, converted from `Edge0/Audio8-TTS-Realistic-Air` revision `925bbd4` (published as Audio8-TTS-Realistic-0.6b and renamed on 2026-11-02, same weights), license Apache-2.0. The references used the collection's pinned Qwen CustomVoice and EmotiVoice ([decisions 8 and 9](../decisions.md)). Python packages pinned in [`uv.lock`](../../experiments/synthetic-call/uv.lock). The gate used Whisper Large v3 MLX `49e6aa28`.
- **Machine:** M2 Pro, 16 GB; runs on 2026-11-28.
- **Kept outside the repository:** the generated audio and references.
