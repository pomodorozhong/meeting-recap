# Experiments

Public summaries of experiments run with the `meeting-experiment-review` skill or before it. Each gives the question, models and pinned versions, settings, runtime and memory, scores and their limits, the decision, and open questions. Recordings, transcripts, names, and full reports stay in the private dataset.

| Date | Experiment | Outcome |
| --- | --- | --- |
| 2026-10-24 | [HushScribe recording trial](2026-10-24-hushscribe-trial.md) | Community-1 merged three voices under one label; per-chunk language detection invented foreign lines |
| 2026-10-24 | [Diarizer settings and models](2026-10-24-diarizer-comparison.md) | Sortformer 29/30 turns; no Community-1 setting past 19 |
| 2026-10-24 | [Transcription settings and models](2026-10-24-transcription-variants.md) | Force Chinese; Breeze-ASR-25 cleanest but too slow through transformers |
| 2026-10-24 | [Attaching labels to text](2026-10-24-label-attachment.md) | Method matters little with short segments; overlap per word chosen |
| 2026-10-24 | [Both full recordings](2026-10-24-full-recordings.md) | Stable labels over 87 minutes, one voice split across two labels; stop testing models |
| 2026-10-29 | [Full calls, Breeze vs. Whisper through MLX](2026-10-29-full-calls-sortformer-breeze-mlx.md) | Breeze through MLX at about 0.25× real time; listening review pending |
