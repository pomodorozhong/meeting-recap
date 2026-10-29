# Handoff

Updated 2026-10-29. Read [AGENTS.md](AGENTS.md) first: this repository is public, and meeting material never enters it.

## Where things stand

The goal is meeting notes produced locally on a MacBook Pro with an M2 Pro and 16 GB of memory, covering the 22 behaviors in the [feature catalogue](https://github.com/pomodorozhong/rabbit-holes/blob/master/topics/ai_meeting_notes/feature-catalogue.md) (`MN-01`–`MN-22`). Research phases 1–3 ran in [rabbit-holes](https://github.com/pomodorozhong/rabbit-holes/issues/167); building continues here.

| Phase | Status |
| --- | --- |
| 1. Feature catalogue | Done, in rabbit-holes |
| 2. Review of open-source local pipelines | Done, in rabbit-holes |
| 3. Recording trial and follow-up experiments | Done: [docs/experiments/](docs/experiments/README.md) |
| 4. Pipeline for saved recordings | Not started |
| 5. App prototype, then the app | Not started |

For a three-person online Chinese + English call on one mono track, Whisper Large v3 with Chinese forced plus FluidAudio's Sortformer kept the speakers apart (29 of 30 reference turns) and ran faster than real time in under 1.6 GB. HushScribe's Community-1 diarizer did not. Breeze-ASR-25 through MLX now runs at about 0.25× real time with Traditional output; whether its text beats Whisper's waits on a listening review.

## Decisions

1. Stop testing models for this kind of call.
2. Pipeline candidate: Whisper Large v3 (Chinese forced) or Breeze-ASR-25, Sortformer, labels attached by overlap per word, a naming step that can merge labels, Traditional script output.
3. Summaries and the other catalogue features are separate questions.
4. Experiments run through the `meeting-experiment-review` skill: private dataset outside Git, public summary in `docs/experiments/`.

## Next steps

1. **Finish the 2026-10-29 listening review** (18 clips), then score Sortformer on both full recordings and compare Breeze with Whisper. Update both reports.
2. **Settle the foundation issues:** [layout for pipeline and app](https://github.com/pomodorozhong/meeting-recap/issues/8), [license](https://github.com/pomodorozhong/meeting-recap/issues/9), [private data backup](https://github.com/pomodorozhong/meeting-recap/issues/7).
3. **Make experiments reproducible without the original call:** [synthetic test recording](https://github.com/pomodorozhong/meeting-recap/issues/4), [Reproduce sections](https://github.com/pomodorozhong/meeting-recap/issues/5), [skill smoke test](https://github.com/pomodorozhong/meeting-recap/issues/6), [migrate the 2026-10-24 results into the dataset](https://github.com/pomodorozhong/meeting-recap/issues/3).
4. **Build the minimal pipeline:** recording in; ASR and Sortformer; attachment; naming; Markdown transcript with times and labels out.
5. **Then summaries, decisions, and action items** (`MN-08`–`MN-10`).

## Open questions

- Does a recording with the presenter's microphone on its own track remove the remaining presenter errors?
- How does the original pyannote Community-1 pipeline compare? It needs the Hugging Face terms accepted for `pyannote/speaker-diarization-community-1`.
- How does Sortformer behave with more than four people, or several people in one room?
- Is a few minutes of hand-made reference transcript worth making, to measure character error rate?
- Should [Who](https://github.com/pomodorozhong/meeting-recap/issues/1) be evaluated for on-device diarization?

## Pending outside this repository

- [rabbit-holes#226](https://github.com/pomodorozhong/rabbit-holes/pull/226) concludes the research topic and points here. It says "Refs #194"; changing it to close rabbit-holes#194 on merge is undecided.
