# HushScribe trial harness

`hushscribe-trial-harness.patch` is the change applied to [HushScribe](https://github.com/drcursor/HushScribe) at `51103f0c8f97344ec7ecdf6480a2ee53cd9a0e92` (3.5.0) for the [2026-10-24 recording trial](../../docs/experiments/2026-10-24-hushscribe-trial.md). HushScribe is MIT-licensed (Copyright (c) 2026 E. Balsa / ebalsa.org); this diff is a derivative of its source and keeps that license.

The patch:

- enables `detectLanguage: true` in the Whisper decoding options (the planned language override);
- when `HUSHSCRIBE_TRIAL_FILE` is set, skips onboarding, selects Whisper Large v3, downloads it, raises the silence timeout to one hour so the download cannot end the file session, and imports the file through **Transcribe File**;
- writes the diarizer's raw segments to `diarization.json` in `HUSHSCRIBE_TRIAL_OUTPUT`, and timings and status to `HUSHSCRIBE_TRIAL_RESULT`;
- sends diagnostic logs to `HUSHSCRIBE_TRIAL_LOG`, also in release builds.

`HUSHSCRIBE_TRIAL_OUTPUT` and `HUSHSCRIBE_TRIAL_RESULT` are required for an automated trial. A trial is completed only after diarization succeeds and its JSON is saved. Export failures are recorded as `failed` in the result JSON and exit nonzero; a failure to save the result itself also exits nonzero with a terminal error. Use a fresh output folder so an old artifact cannot be mistaken for this trial's output.

## Reproduce

Needs Xcode 26.3+ on Apple Silicon with macOS 26.

```bash
git clone https://github.com/drcursor/HushScribe.git
cd HushScribe
git checkout 51103f0c8f97344ec7ecdf6480a2ee53cd9a0e92
git apply /path/to/meeting-recap/experiments/hushscribe-harness/hushscribe-trial-harness.patch
scripts/release.sh test
```

Then run the built app binary with the environment set (all paths outside this repository):

```bash
HUSHSCRIBE_TRIAL_FILE=/private/recording.mp4 \
HUSHSCRIBE_TRIAL_OUTPUT=/scratch/hushscribe-out \
HUSHSCRIBE_TRIAL_RESULT=/scratch/hushscribe-result.json \
HUSHSCRIBE_TRIAL_LOG=/scratch/hushscribe.log \
  /path/to/HushScribe.app/Contents/MacOS/HushScribe
```

Register `diarization.json` as a `segments` run with the review skill. The transcript HushScribe writes is in its own Markdown format, not the `transcript` artifact format.
