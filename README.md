# meeting-recap

A fully local AI meeting assistant that records, transcribes, and summarizes meetings on your device.

## Status

Research and experiments. On an M2 Pro / 16 GB Mac, Whisper Large v3 with Chinese forced plus FluidAudio's Sortformer diarizer produced a usable transcript and kept the speakers apart on a three-person Chinese + English call. The next step is a pipeline for saved recordings. See [HANDOFF.md](HANDOFF.md) for the plan and [docs/experiments/](docs/experiments/) for every experiment.

## Layout

| Path | Holds |
| --- | --- |
| [docs/experiments/](docs/experiments/) | Public summary of each experiment: question, pinned setup, runtime, scores, decision, open questions. |
| [docs/](docs/) | [Investigation plan](docs/investigation-plan.md), [review guide](docs/review-guide.md), [runner guide](docs/runners.md). |
| [experiments/](experiments/) | Model runners used by the experiments. |
| [.agents/skills/meeting-experiment-review/](.agents/skills/meeting-experiment-review/) | Agent skill for running experiments on private recordings, listening reviews, and scoring. |

Recordings, transcripts, and listening answers never enter this repository; see [AGENTS.md](AGENTS.md). Background research (feature catalogue, paid products, open-source pipelines) is in [rabbit-holes](https://github.com/pomodorozhong/rabbit-holes/tree/master/topics/ai_meeting_notes).
