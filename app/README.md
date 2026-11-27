# App prototype

A macOS window that records a call's audio and your microphone for real, and shows a **mock** transcript and recap. It isn't connected to any pipeline. See [decision 17](../docs/decisions.md) for why.

| Part | Status |
| --- | --- |
| Recording | Real. System audio and the microphone go to two lossless files on one timeline, as in [`experiments/capture/`](../experiments/capture/README.md). The Meeting tab holds the source settings and the live recorder before and during a recording, and playback after it. |
| Recordings list | Real. Each recording shows its date, length and a status pill; the title can be renamed. |
| Meeting tab for a recording | Real. A player that stays on screen above the rest: the timeline below, and playback of both tracks together (click the timeline to jump), and below it the gaps filled in and audio dropped. |
| Timeline and typed notes | Real. The Meeting tab shows one timeline during and after a recording: a Turns row (with screenshots above it) and a Notes row across the whole meeting. While recording it shows a fixed two-minute window that fills from the left and then slides with the recording, settles each half second's turn once so earlier turns never change, has an Overview row above it with the whole recording so far and a frame around the stretch shown, and has the timer and Stop in place of playback; afterwards it plays back and clicking jumps. For a real recording, Turns shows who was talking from the two tracks' loudness until the transcript is connected: you in your color, anyone on the call in grey, since who that is isn't known yet. Under the timeline is the feed of your notes; while recording, a box at the bottom takes one note per line, timed from its first character to Return on the recording's timeline, and saves to `notes.txt` as you type. A finished note can be fixed and keeps its times. The sample meetings have a few invented notes. Notes can't be added after the recording yet, and aren't fed to the recap. **New meeting (demo)** in the sidebar, or `open app/.build/MeetingRecap.app --args --demo`, runs the recording screen with invented sound and saves nothing, so the design can be seen without the permissions. |
| Meeting feed and recap | Mock, and only for the two sample meetings in the list. [`Fixtures.swift`](Sources/MeetingRecap/Fixtures.swift) holds two invented meetings: labeled lines with one unsure speaker, drawn stand-ins for screenshots placed at their times, and a recap whose every item cites lines. On the Meeting tab the feed of lines and screenshots sits under the player; clicking a line, a screenshot or the turns strip moves the playhead. A sample has no audio, so its playhead is simulated. The app doesn't capture screenshots yet. A real recording shows only the player, and "Not processed yet" on the Recap tab. |
| Pipeline | Not connected. Phase 5 of the [status](../docs/README.md) says when. |

The window uses Liquid Glass, so it needs macOS 26.

## Build and run

Needs macOS 26 and the Command Line Tools; no Xcode project.

```bash
app/scripts/bundle.sh
open app/.build/MeetingRecap.app
```

Add `--test` to run the tests first. The first Record asks for **Microphone** and **Screen & System Audio Recording**; after allowing the second, quit and reopen the app. The bundle is signed ad hoc, so a rebuild that changes the code changes its signature; `bundle.sh` then clears both permissions, and the next Record asks for them again (allow, then quit and reopen). If the app is running, the script leaves the permissions alone and prints the commands to run after you quit it.

### If Record says permission is off

System Settings can show Meeting Recap as allowed while recording still fails. macOS ties each permission to the exact build it was granted to, and an ad hoc signature changes whenever the code changes, so the switch in Settings can belong to an older build. Every build also shares the bundle ID `local.meeting-recap.app`, so two builds in different checkouts or worktrees share one permission entry, and whichever was granted last takes it from the other.

`bundle.sh` clears them after each rebuild that changes the signature. If you switch to another build without rebuilding, or the script skipped the reset because the app was running, quit every copy of the app, then clear both permissions:

```bash
tccutil reset ScreenCapture local.meeting-recap.app
tccutil reset Microphone local.meeting-recap.app
```

Open only the build you want to use, press Record, allow both permissions, then quit and reopen it. Don't open another build afterwards, or the permissions move to it. Switching the setting off and on in System Settings doesn't help, because it keeps the stale entry.

## Where recordings go

`~/Library/Application Support/MeetingRecap/Recordings/<date and time>/` holding `system.m4a`, `mic.m4a` and `timing.json`, plus `notes.txt` when you typed notes (a header, then `start<TAB>end<TAB>note` per line, in seconds on the same timeline as `timing.json`). The app refuses a folder inside a Git checkout or one that already holds files. This is not the review dataset at `$MEETING_REVIEW_DATA`; copy a recording there by hand to run experiments on it.

Wear headphones, or the other side of the call leaks into the microphone file. The options and file details are as in the [capture README](../experiments/capture/README.md).

## Layout

| Path | Holds |
| --- | --- |
| `Sources/RecorderCore/` | The recorder as a library: tracks and timeline padding, the capture session, folder safety rules, the notes file, and the list of recordings. |
| `Sources/MeetingRecap/` | The SwiftUI shell: collapsible meeting list, and the Meeting and Recap tabs. |
| `Tests/RecorderCoreTests/` | Folder rules, the notes file, the recordings list, and a real file write with a dropout and a late start. Generated audio only. |
| `scripts/bundle.sh` | Builds, optionally tests, and wraps the app in a bundle. |

## What is and isn't checked

- Tests pass for the folder rules, the recordings list, silence padding, and both files ending the same length after a dropout.
- The sample meetings' Meeting and Recap tabs and the new-meeting setup screen render as intended (screenshots). Not exercised by clicking: choosing a speaker on the unsure line, the check bar's Previous and Next, citation jumps, action checkboxes, Copy and Save, collapsing the list.
- Not checked: a real recording through ScreenCaptureKit from the app, the permission prompts, recording from a single app, the live waveforms, and playback and waveforms of a real recording. Those need a person to record something.
- The call source is a picker of the apps running now, call apps first. A recording from one app (rather than everything) has not been tried.
