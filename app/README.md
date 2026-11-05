# App prototype

A macOS window that records a call's audio and your microphone for real, and shows a **mock** transcript and recap. It isn't connected to any pipeline. See [decision 16](../docs/decisions.md) for why.

| Part | Status |
| --- | --- |
| Recording | Real. System audio and the microphone go to two lossless files on one timeline, as in [`experiments/capture/`](../experiments/capture/README.md). The Audio tab holds the source settings, the live recorder, and playback. |
| Recordings list | Real. Each recording shows its date, length and a status pill; the title can be renamed. |
| Audio tab for a recording | Real. Waveforms of both tracks, playback of both together (click a track to jump), and the gaps filled in and audio dropped. |
| Timeline and recap | Mock, and only for the two sample meetings in the list. [`Fixtures.swift`](Sources/MeetingRecap/Fixtures.swift) holds two invented meetings: labeled lines with one unsure speaker, drawn stand-ins for screenshots placed at their times, and a recap whose every item cites lines. The Timeline tab shows speech and screenshots in time order under an overview strip. The app doesn't capture screenshots yet. A real recording shows "Not processed yet" on those tabs. |
| Pipeline | Not connected. Phase 5 of the [status](../docs/README.md) says when. |

The window uses Liquid Glass, so it needs macOS 26.

## Build and run

Needs macOS 26 and the Command Line Tools; no Xcode project.

```bash
app/scripts/bundle.sh
open app/.build/MeetingRecap.app
```

Add `--test` to run the tests first. The first Record asks for **Microphone** and **Screen & System Audio Recording**; after allowing the second, quit and reopen the app. The bundle is signed ad hoc, so macOS may ask again after a rebuild.

## Where recordings go

`~/Library/Application Support/MeetingRecap/Recordings/<date and time>/` holding `system.m4a`, `mic.m4a` and `timing.json`. The app refuses a folder inside a Git checkout or one that already holds files. This is not the review dataset at `$MEETING_REVIEW_DATA`; copy a recording there by hand to run experiments on it.

Wear headphones, or the other side of the call leaks into the microphone file. The options and file details are as in the [capture README](../experiments/capture/README.md).

## Layout

| Path | Holds |
| --- | --- |
| `Sources/RecorderCore/` | The recorder as a library: tracks and timeline padding, the capture session, folder safety rules, and the list of recordings. |
| `Sources/MeetingRecap/` | The SwiftUI shell: collapsible meeting list, and the Audio, Timeline and Recap tabs. |
| `Tests/RecorderCoreTests/` | Folder rules, the recordings list, and a real file write with a dropout and a late start. Generated audio only. |
| `scripts/bundle.sh` | Builds, optionally tests, and wraps the app in a bundle. |

## What is and isn't checked

- Tests pass for the folder rules, the recordings list, silence padding, and both files ending the same length after a dropout.
- The sample meetings' Audio, Timeline and Recap tabs and the new-meeting setup screen render as intended (screenshots). Not exercised by clicking: choosing a speaker on the unsure line, the check bar's Previous and Next, citation jumps, action checkboxes, Copy and Save, collapsing the list.
- Not checked: a real recording through ScreenCaptureKit from the app, the permission prompts, recording from a single app, the live waveforms, and playback and waveforms of a real recording. Those need a person to record something.
- The call source is a picker of the apps running now, call apps first. A recording from one app (rather than everything) has not been tried.
