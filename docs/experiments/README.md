# Experiments

Public summaries of experiments run with the `meeting-experiment-review` skill or before it. Each gives the question, models and pinned versions, settings, runtime and memory, scores and their limits, the decision, and open questions. Recordings, transcripts, names, and full reports stay in the private dataset.

Each summary is written from [TEMPLATE.md](TEMPLATE.md) and committed **before** the experiment's first run, with the entry point that reruns it, its question, and its plan (decisions 4 and 11). It is completed as results come in; its status line says how far it got. Experiments from 2026-10-24 predate these rules and were written afterwards, and the 2026-10-30 experiment predates the entry-point rule.

| Date | Experiment | Outcome |
| --- | --- | --- |
| 2026-10-24 | [HushScribe recording trial](2026-10-24-hushscribe-trial.md) | Community-1 merged three voices under one label; per-chunk language detection invented foreign lines |
| 2026-10-24 | [Diarizer settings and models](2026-10-24-diarizer-comparison.md) | Sortformer 29/30 turns; no Community-1 setting past 19 |
| 2026-10-24 | [Transcription settings and models](2026-10-24-transcription-variants.md) | Force Chinese; Breeze-ASR-25 cleanest, and fast enough through MLX (2026-10-29 follow-up) |
| 2026-10-24 | [Attaching labels to text](2026-10-24-label-attachment.md) | Method matters little with short segments; overlap per word chosen |
| 2026-10-24 | [Both full recordings](2026-10-24-full-recordings.md) | Stable labels over 87 minutes, one voice split across two labels; stop testing models |
| 2026-10-30 | [Sortformer on a two-person two-track call](2026-10-30-two-track-call.md) | Planned |
| 2026-11-02 | [Recognizers and language on 17 synthetic recordings](2026-11-02-synthetic-collection-recognition.md) | Declaring the language helped all six English calls; Turbo fastest, but full Whisper made fewer errors on six calls |
| 2026-11-02 | [Diarizers and attachment on 17 synthetic recordings](2026-11-02-synthetic-collection-speakers.md) | Who about 95× faster in total but merged speakers on clean four-person calls; word attachment recovered the most turns |
| 2026-11-02 | [Digital silence on 17 synthetic recordings](2026-11-02-synthetic-collection-silence.md) | Exact-zero splitting lowered Mandarin error for full Whisper and Turbo and hurt Breeze; all-zero input now skips recognition and the recap |
| 2026-11-02 | [Recap facts and citations on 17 synthetic recordings](2026-11-02-synthetic-collection-recaps.md) | Better transcripts didn't ensure better notes (7/9, 6/9, 6/9 facts); per-segment lines improved citation support |
| 2026-11-04 | [Recap stage, then whole pipelines, on real calls](2026-11-04-recap-stage-real-calls.md) | Planned |
