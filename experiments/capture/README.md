# Capture

Records a call's system audio and the microphone to separate files, for test data with a known split between the local speaker and everyone else. It uses ScreenCaptureKit (macOS 15+), the same OS feature meeting-note apps use, so it needs no virtual audio device and leaves the audio output alone. Other recorders, such as a meeting-notes app, can run at the same time.

## Run

From the repository root, a few seconds before the call:

```bash
swift experiments/capture/record.swift
```

Every 5 seconds it prints the elapsed time and the peak level of each track since the last line, so you can see that both are live. Stop with Ctrl-C.

| Option | Does |
| --- | --- |
| `--app <name>` | Capture system audio only from apps whose name or bundle ID contains `<name>` (repeatable), such as `--app Teams` or `--app Chrome` for Google Meet. Without it, all system audio is captured. |
| `--mic <name>` | Record the input device whose name contains `<name>`, such as `--mic MacBook`. Without it, the system default input is used. |
| `--out <dir>` | Output folder. The default is `$MEETING_REVIEW_DATA/raw/<date and time>/`, outside the checkout. |

To see the microphone names `--mic` can match, pass a name that matches none; the script stops and lists them. Quote it, since zsh treats a bare `?` as a filename pattern:

```bash
swift experiments/capture/record.swift --mic '?'
```

The first run asks to allow **Screen & System Audio Recording** and **Microphone** for your terminal app (System Settings > Privacy & Security). Restart the terminal after granting them.

## Output

| File | Holds |
| --- | --- |
| `system.m4a` | System audio, Apple Lossless, 48 kHz stereo |
| `mic.m4a` | The input device, Apple Lossless, resampled to 48 kHz mono |
| `timing.json` | Per track: where its first real sample falls, its duration, and how much silence was filled in |

Both files share one timeline that starts at the first audio buffer from either stream. A track that starts late or drops out is filled with silence, so sample *n* of one file is sample *n* of the other. Convert for other tools with, for example, `ffmpeg -i mic.m4a -ar 16000 mic.wav`.

Wear headphones: on speakers, the other side of the call leaks into `mic.m4a`. A Bluetooth headset's mic runs at 16 or 24 kHz and switches the headset into its lower-quality call mode, so for cleaner mic audio use wired headphones or Bluetooth headphones with `--mic MacBook`.

`excludesCurrentProcessAudio` must stay off: ScreenCaptureKit applies it to the whole app that launched the script, which would drop audio played by anything run from the same terminal.
