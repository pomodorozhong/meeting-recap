# App prototype

A macOS window that records a call's audio and your microphone for real, and shows a **mock** transcript and recap. It isn't connected to any pipeline. See [decision 16](../docs/decisions.md) for why.

| Part | Status |
| --- | --- |
| Recording | Real. System audio and the microphone go to two lossless files on one timeline, as in [`experiments/capture/`](../experiments/capture/README.md). |
| Recordings list | Real. Reads each recording's `timing.json`; shows its length, silence filled in, audio the encoder dropped, and any write error. |
| Transcript and recap | Mock. [`Fixtures.swift`](Sources/MeetingRecap/Fixtures.swift) holds an invented three-speaker call with a recap whose every item cites transcript lines. Every recording shows this same sample, under a banner saying so. |
| Pipeline | Not connected. Phase 5 of the [status](../docs/README.md) says when. |

## Build and run

Needs macOS 15 or later and the Command Line Tools; no Xcode project.

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
| `Sources/MeetingRecap/` | The SwiftUI shell: record bar with live meters, recordings list, mock review screen. |
| `Tests/RecorderCoreTests/` | Folder rules, the recordings list, and a real file write with a dropout and a late start. Generated audio only. |
| `scripts/bundle.sh` | Builds, optionally tests, and wraps the app in a bundle. |

## What is and isn't checked

- Tests pass for the folder rules, the recordings list, silence padding, and both files ending the same length after a dropout.
- The window renders and the mock screen shows as intended.
- Not checked: a real recording through ScreenCaptureKit from the app, the permission prompts, and the "only this app's audio" filter. Those need a person to click Record on a call.
- The app filter is a text box matched against app names; a picker of running apps is a follow-up.
