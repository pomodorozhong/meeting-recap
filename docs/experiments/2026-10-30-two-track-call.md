# 2026-10-30: Sortformer on a two-person call, scored against its own tracks

**Status:** planned

Write and commit this file before the first run. Fill in the results sections as the experiment goes; nothing here may name people, quote transcripts, or give private paths.

## Question

On a two-person online call recorded as two tracks, does each track's activity agree with what the user hears, well enough to serve as the speaker reference (decision 6)? And against that reference, how many turns does Sortformer recover on the mixed audio?

## Goal and assumptions

- **Decision it informs:** whether `review.py tracks` can replace listening sessions for two-person two-track calls, and whether Sortformer still holds up as the pipeline's diarizer (decision 2) on a kind of call it has not been tested on: two people, not three, with many short replies.
- **Builds on:** [diarizer comparison](2026-10-24-diarizer-comparison.md) (Sortformer 29/30 turns on a three-person excerpt) and [both full recordings](2026-10-24-full-recordings.md) (stable labels over 87 minutes). The synthetic call (#4) scored Sortformer 67/72 turns with `review.py known`.
- **Assumptions:** exactly two speakers, as the user confirmed; a meeting app's own transcript of the call shows three speakers and is not used. The local speaker wore headphones, so the mic track holds only Speaker A and the system track only Speaker B. The tracks share one timeline (the recorder fills gaps with silence). Sortformer's models are already cached. Nothing else runs during the timed Sortformer run.
- **Expected result:** track activity matches the listened order on at least 8 of the 10 check clips, with misses at short backchannels or laughs. Sortformer recovers most turns but drops short replies, so with about 7 turns per 30 s reference clip, fewer than half of its clips are fully correct. If track activity fails more than 2 check clips, the activity settings are revisited (a new reference ID, recorded here) before Sortformer's score is reported. If Sortformer recovers under 80% of turns, two-person calls need a closer look before the pipeline relies on it.

## Input

One online Chinese + English call between two people (Speakers A and B), 48:30, recorded with [`experiments/capture/`](../../experiments/capture/) as two Apple Lossless tracks at 48 kHz: the microphone (Speaker A, headphones) and system audio (Speaker B). The registered recording is a mono AAC mix of the two tracks; runners use a 16 kHz mono WAV of that mix, and the reference uses 16 kHz mono 16-bit WAVs of each track.

Dataset recording ID: `two-track-call`, group `two-track-call`.

## Plan

Scratch files (`mic.wav`, `system.wav`, `call.m4a`, `call-16k.wav`) stay outside the checkout; skill scripts run from `.agents/skills/meeting-experiment-review/`:

```bash
ffmpeg -i mic.m4a -ac 1 -ar 16000 mic.wav
ffmpeg -i system.m4a -ac 1 -ar 16000 system.wav
ffmpeg -i mic.m4a -i system.m4a -filter_complex "[0]aformat=channel_layouts=mono[a];[1]aformat=channel_layouts=mono[b];[a][b]amix=inputs=2:normalize=0" -c:a aac -b:a 128k call.m4a
ffmpeg -i call.m4a -ac 1 -ar 16000 -c:a pcm_f32le call-16k.wav
python3 scripts/dataset.py add-recording "$MEETING_REVIEW_DATA" --id two-track-call --audio call.m4a --duration <ffprobe duration> --group two-track-call
```

| Run ID | Model and pinned version | Settings | Command |
| --- | --- | --- | --- |
| `tracks-two-track-call` | `scripts/tracks.py` (level gate per track, skill code below) | defaults: 30 ms frames, 15 dB over the 10th-percentile level, floor −50 dBFS, gaps under 0.3 s merged, runs under 0.2 s dropped | `python3 scripts/tracks.py --track A=mic.wav --track B=system.wav --out segments.json` |
| `sortformer-two-track-call` | FluidAudio `ea500621819cadc46d6212af44624f2b45ab3240`, `Sortformer_v2.1` (weights pinned in [runners](../runners.md)) | defaults | `/usr/bin/time -l experiments/diarization/.build/release/fluidaudiocli sortformer call-16k.wav --output sortformer.json`, then `experiments/diarization/sortformer_to_segments.py sortformer.json segments.json` |

The track activity is registered as a run so the review page can show it next to each clip and the check can score it.

**Track reference** (no listening): `tracks-two-track-call`, built with

```bash
python3 scripts/review.py tracks "$MEETING_REVIEW_DATA" --recording two-track-call --track A=mic.wav --track B=system.wav --id tracks-two-track-call
```

at the default 30 s window. A dry run on scratch copies gave 86 clips, about 31 s each.

**Check clips** (listening): 10 `speaker_order` clips of 15 s. Six come from `pick_clips.py` on the track activity, one per time bin; four are added by hand at the four longest stretches where both tracks are active, at least 60 s from each other and from the picked clips, each window starting 4 s before the overlap. The plan records the hand-added clips under `selector.method`.

```json
{"id": "check-two-track-call", "question": "Does each track's activity match who you hear, and in what order?",
 "seed": 20261030, "max_turns": 6,
 "recordings": [{"recording_id": "two-track-call", "diarization_run": "tracks-two-track-call", "speaker_clips": 6,
                 "speaker_show_runs": ["tracks-two-track-call", "sortformer-two-track-call"]}]}
```

Skill code: commit `a6c7e69`; dataset snapshot `de616b4aa3dcbd29b96057fbdc173f37dbe160f3b898c035d62802a8d1441f23` (from `dataset.py snapshot`). Restarts and reruns use this snapshot, not the current scripts.

Review session ID: `check-two-track-call`. Reference IDs: `ref-check-two-track-call` (listened) and `tracks-two-track-call` (from the tracks). Evaluation IDs: `eval-check-two-track-call` (both runs against the listened clips) and `eval-two-track-call` (Sortformer against the track reference).

## Run the review

```bash
python3 .agents/skills/meeting-experiment-review/scripts/review.py serve "$MEETING_REVIEW_DATA" --session check-two-track-call --port 8770
```

Run from the repository root with `MEETING_REVIEW_DATA` set to the private dataset ([setup](../../README.md#setup)). Open the `http://127.0.0.1:8770/?token=…` URL it prints; answers save as you go, and Ctrl-C stops the server. Click **Finish session** when done. Use `A` for yourself and `B` for the other person in every clip.

## Restart from scratch

If the private data for this experiment is lost: register the recording again under the same ID from the two raw tracks with the commands above, rerun the runs, register them under the same IDs, rebuild the track reference, and rerun `pick_clips.py` with the config above, using the skill code at the commit above (`git show a6c7e69:.agents/skills/meeting-experiment-review/scripts/…`) if the snapshot is lost too. Track activity is deterministic, so the same tracks give the same reference and the same picked clips; rechoose the four hand-added clips by the rule above.

## Runtime and memory

## Results

| Measure | Result |
| --- | --- |
| Track activity vs. listened clips | |
| Sortformer vs. listened clips | |
| Sortformer vs. track reference: turns recovered | |
| Sortformer vs. track reference: clips correct | |
| Excluded items | |
| Label mapping | |

**Metric limits.** Both scores measure speaker turn order within clips, not DER, timing, or transcript accuracy. The track reference is itself a measurement (a level gate); the listened check is what makes it a reference, and only on 10 clips.

## Decision

## Open questions
