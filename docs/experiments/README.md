# Experiments

Public summaries of experiments run with the `meeting-experiment-review` skill or before it. Each gives the question, models and pinned versions, settings, runtime and memory, scores and their limits, the decision, and open questions. Recordings, transcripts, names, and full reports stay in the private dataset.

Each summary is written from [TEMPLATE.md](TEMPLATE.md) and committed **before** the experiment's first run, with its goal, assumptions, plan, and the command that starts the listening review. It is completed as results come in; its status line says how far it got. Experiments from 2026-10-24 predate this rule and were written afterwards.

| Date | Experiment | Outcome |
| --- | --- | --- |
| 2026-10-24 | [HushScribe recording trial](2026-10-24-hushscribe-trial.md) | Community-1 merged three voices under one label; per-chunk language detection invented foreign lines |
| 2026-10-24 | [Diarizer settings and models](2026-10-24-diarizer-comparison.md) | Sortformer 29/30 turns; no Community-1 setting past 19 |
| 2026-10-24 | [Transcription settings and models](2026-10-24-transcription-variants.md) | Force Chinese; Breeze-ASR-25 cleanest, and fast enough through MLX (2026-10-29 follow-up) |
| 2026-10-24 | [Attaching labels to text](2026-10-24-label-attachment.md) | Method matters little with short segments; overlap per word chosen |
| 2026-10-24 | [Both full recordings](2026-10-24-full-recordings.md) | Stable labels over 87 minutes, one voice split across two labels; stop testing models |
