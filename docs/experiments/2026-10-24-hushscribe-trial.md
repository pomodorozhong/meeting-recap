# 2026-10-24: HushScribe recording trial

**Status:** complete. Speaker separation failed; follow-up experiments on the same day replaced the diarizer and the language setting.

## Question

Can the setup selected in the configuration review, a HushScribe source build with Whisper Large v3, per-chunk language detection, and FluidAudio's offline Community-1 diarizer, turn a real Chinese + English call into a usable transcript with reliable speaker labels on the target Mac?

## Input

The first 10:00 of an online design-review call among three people (Speakers A, B, and C), Mandarin with English product terms. Recorded by a paid meeting assistant and exported as one mono track (AAC, 48 kHz); how it captured and mixed participants is not known.

## Models and settings

| Component | Version | Settings |
| --- | --- | --- |
| HushScribe | 3.5.0, `51103f0c8f97344ec7ecdf6480a2ee53cd9a0e92`, plus the [trial harness patch](../../experiments/hushscribe-harness/) | **Transcribe File** path; `detectLanguage: true`; silence timeout raised to one hour so a model download cannot end the session |
| WhisperKit | 0.18.0, `e2adabbe7d98dc4d0ab9a5b75424ecc42a9cdbef` | as pinned by HushScribe |
| Whisper model | `argmaxinc/whisperkit-coreml/openai_whisper-large-v3` (2.9 GB); `TextDecoder.mlmodelc/weights/weight.bin` SHA-256 `680f398925225a313c62da0221aa0a58c9f1bffac5c36f20c449a70a7c9b1e55` | language detected per chunk |
| FluidAudio | `ea500621819cadc46d6212af44624f2b45ab3240` | `OfflineDiarizerManager()` defaults: clustering threshold 0.6, no speaker count |

Host: Apple M2 Pro, 16 GB, macOS 26.6.2 (25G83). Three runs were made; the first two failed for harness reasons (an empty transcript, and a stop after about two minutes) and only the third is used.

## Runtime and memory

| Step | Time for 600 s of audio |
| --- | ---: |
| Model load (already downloaded) | 4.9 s |
| Transcription | 241 s |
| Speaker separation and saving | 29 s |

Memory was not recorded.

## Results

**Speaker separation.** The diarizer reported two labels for three people: one with 89 segments and 313.5 s of speech, the other with 3 segments and 5.7 s. The large label covers all three voices, so no turn can be attributed. The raw diarizer output already holds one substantial speaker, so the failure is in the diarizer, not in the attachment step.

The attachment step has two further problems that would remain with a better diarizer: each transcript line is labeled by looking up one whole second near the end of its speech, so a line containing two people gets one label; and the saved header reports one speaker although two labels appear.

**Transcription.** Read in order, the transcript follows the meeting. Errors fall into four groups:

- names of participants misheard (three instances);
- words that change meaning, such as a mechanism name heard as an unrelated phrase (several instances);
- six invented lines in Norwegian, Korean, German, or English on short or quiet chunks, caused by detecting the language for every chunk;
- about twelve lines in Simplified rather than Traditional Chinese.

The two longest gaps in the transcript also have no speech in the diarizer output, so they are probably pauses, not dropped text.

| Measure | Result |
| --- | --- |
| Speaker labels | 2 labels for 3 people; one covers 98% of labeled speech |
| Invented foreign-language lines | 6 |
| Lines in Simplified script | about 12 |

**Metric limits.** Speaker results come from comparing the output with the conversation's structure and the confirmed identities; the 14-clip listening reference was made afterwards (see the [diarizer comparison](2026-10-24-diarizer-comparison.md)). Word errors marked as probable were inferred from context, not checked by ear. No character error rate was measured.

## Decision

The setup as shipped is not usable for attributed notes: speaker separation must change before transcription errors matter. Test other diarizers and diarizer settings, and force the transcription language.

## Open questions

- Did the mono export discard a separate microphone track that would have made the presenter easy to separate?
- How does the original pyannote Community-1 pipeline compare with FluidAudio's conversion?
