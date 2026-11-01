# Project status

The goal is meeting notes produced locally on a MacBook Pro with an M2 Pro and 16 GB of memory, covering the 22 behaviors in the [feature catalogue](https://github.com/pomodorozhong/rabbit-holes/blob/master/topics/ai_meeting_notes/feature-catalogue.md) (`MN-01`–`MN-22`). Research phases 1–3 ran in [rabbit-holes](https://github.com/pomodorozhong/rabbit-holes/issues/167); building continues here. What to work on next is in [HANDOFF.md](../HANDOFF.md).

| Phase | Status |
| --- | --- |
| 1. Feature catalogue | Done, in rabbit-holes |
| 2. Review of open-source local pipelines | Done, in rabbit-holes |
| 3. Recording trial and follow-up experiments | Done: [experiments](experiments/README.md) |
| 4. Pipeline for saved recordings | In progress: [whisper-sortformer](../experiments/pipelines/whisper-sortformer/README.md) runs end to end on the synthetic call; private-recording review next |
| 5. App prototype, then the app | Not started |

For a three-person online Chinese + English call on one mono track, Whisper Large v3 with Chinese forced plus FluidAudio's Sortformer kept the speakers apart (29 of 30 reference turns) and ran faster than real time in under 1.6 GB. HushScribe's Community-1 diarizer did not. Breeze-ASR-25 through MLX runs at about 0.25× real time with Traditional output; the [synthetic collection benchmark](experiments/2026-11-01-synthetic-collection.md) compares its text directly with Whisper on generated references. Accuracy on private calls still needs a confirmed transcript. The [ten-call action benchmark](experiments/2026-11-01-action-evidence.md) measures whether final assignments and their citations survive transcription and extraction. Its [methodology review](experiments/2026-11-01-action-evidence-review.md) identifies unproven assumptions; the [grounding test plan](experiments/2026-11-01-action-grounding-plan.md) defines the next unattended checks, with input fixtures prepared but no new inference results.

## Decisions

See [decisions.md](decisions.md). Pipeline candidate: Whisper Large v3 (Chinese forced) or Breeze-ASR-25, Sortformer, labels attached by overlap per word, a naming step that can merge labels, Traditional script output.

## Open questions

- Does a recording with the presenter's microphone on its own track remove the remaining presenter errors?
- How does the original pyannote Community-1 pipeline compare? It needs the Hugging Face terms accepted for `pyannote/speaker-diarization-community-1`.
- How does Sortformer behave with more than four people, or several people in one room?
- Is a few minutes of hand-made reference transcript worth making, to measure character error rate?

## Documents

- [Decisions](decisions.md): what was decided, including the repository layout.
- [Experiments](experiments/README.md): one public summary per experiment, and the template for new ones.
- [Runner guide](runners.md): how each model runner is built and run, with pinned versions.
- [Investigation plan](investigation-plan.md) and [review guide](review-guide.md): the research plan and review criteria from phases 1–3.
