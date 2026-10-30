# 2026-10-30: Who against Sortformer

**Status:** planned

Write and commit this file before the first run. Fill in the results sections as the experiment goes; nothing here may name people, quote transcripts, or give private paths.

## Question

Does Desert Ant Labs' Who diarizer ([#1](https://github.com/pomodorozhong/meeting-recap/issues/1)) keep speakers apart as well as Sortformer on this project's kind of calls, and is it faster or lighter on the M2 Pro? Does its voice matching across five-minute pieces avoid Sortformer's one voice split across two labels on long calls?

## Goal and assumptions

- **Decision it informs:** whether Who replaces Sortformer as the pipeline's diarizer (decision 2), stays an optional alternative, or is dropped.
  - Replace: Who recovers at least as many turns as Sortformer on every scored recording, gives no more labels than there are people on the long calls, and runs faster.
  - Optional alternative: within 5% of Sortformer's turns recovered, or better on one recording and worse on another.
  - Drop: more than 5% fewer turns on any scored recording.
- **Builds on:**
  - The [diarizer comparison](2026-10-24-diarizer-comparison.md): Sortformer recovered 29/30 turns on a three-person excerpt. That excerpt is not in the review dataset yet (#3), so it is not rerun here.
  - [Both full recordings](2026-10-24-full-recordings.md): Sortformer kept labels stable over 87 minutes but split one voice across two labels.
  - The [synthetic call](../../experiments/synthetic-call/README.md): Sortformer recovered 67/72 turns.
  - The [two-track call](2026-10-30-two-track-call.md): Sortformer recovered 528/629 turns against track activity. That score is provisional until its listening check.
- **Assumptions:**
  - Who 0.3.4 is the weights revision that SDK 4.2.1 pins. Weights are downloaded once into a model folder outside the checkout before any timed run.
  - The SDK's default settings are used, with no speaker-share filter, so brief speakers stay visible.
  - Who is built for at most four speakers per five-minute piece; every recording here has two or three people.
  - Nothing else runs during timed runs. Sortformer's models are already cached.
- **Expected result:**
  - Who matches Sortformer within a few turns on the synthetic call and the two-track call, and runs many times faster.
  - On the synthetic call, Who keeps the four overlapping turns, which a single-label view drops anyway.
  - On the long calls, Who's numbering across pieces should hold, giving three labels for three people. A fourth label with real speaking time would be the same failure as Sortformer's split.
  - The vendor's numbers are for English. Mandarin with English terms, and many short replies, may cost Who more turns than the vendor's AMI score suggests.

## Input

| Recording ID | Group | Profile |
| --- | --- | --- |
| `synthetic` | `synthetic-call` | The shareable synthetic call (#4): 5:30, three generated voices, Taiwanese Mandarin with English terms, one track, with four overlaps and short interjections. Ground truth from its script. |
| `two-track-call` | `two-track-call` | 48:30 online Chinese + English call between two people, recorded on two tracks and mixed to mono. |
| `part1`, `part2` | `call-2026-10-22` | 22:23 and 64:49 parts of one online Chinese + English call among three people, one mono track. |

Runners get 16 kHz mono WAVs:
- the synthetic call's own `call.wav`, SHA-256 `6b7011c6…2a25d48` as in its `reference/manifest.json`;
- for the others, `ffmpeg -i <registered source> -ac 1 -ar 16000 -c:a pcm_f32le <id>-16k.wav`, the same conversion the earlier Sortformer runs used.

## Plan

The runner is [`experiments/who/`](../../experiments/who/): Swift package `whoexp` on `desert-ant-core` `1a5efed67f44731b5eb5433aa9be3eebae05e269` (tag `v4.2.1`), product `Who`.
- Weights: [`desert-ant-labs/who`](https://huggingface.co/desert-ant-labs/who) revision `v0.3.4`, Core ML, `coreml-fp16` or `coreml-int8`.
- It writes `segments` with every speaker kept and prints the load and diarize times.
- `WHO_MODELS` is the model folder outside the checkout.

```bash
cd experiments/who && swift build -c release
/usr/bin/time -l experiments/who/.build/release/whoexp <id>-16k.wav segments.json variant=fp16 models="$WHO_MODELS"
```

| Run ID | Model and pinned version | Settings | Command |
| --- | --- | --- | --- |
| `who-fp16-synthetic` | Who v0.3.4 fp16, SDK 4.2.1 | defaults, no share filter | as above, `variant=fp16` |
| `who-int8-synthetic` | Who v0.3.4 int8, SDK 4.2.1 | defaults, no share filter | as above, `variant=int8` |
| `sortformer-synthetic` | FluidAudio `ea500621819cadc46d6212af44624f2b45ab3240`, `Sortformer_v2.1` | defaults | `fluidaudiocli sortformer call.wav --output sortformer.json`, then `sortformer_to_segments.py` ([runners](../runners.md)) |
| `who-fp16-two-track-call`, `who-int8-two-track-call` | Who v0.3.4 fp16 / int8 | defaults, no share filter | as above |
| `who-fp16-part1`, `who-int8-part1`, `who-fp16-part2`, `who-int8-part2` | Who v0.3.4 fp16 / int8 | defaults, no share filter | as above |

The comparison runs already registered are `sortformer-two-track-call`, `sortformer-part1` and `sortformer-part2`.

**Repeats and setup.**
- The first fp16 and int8 runs download the weights; that time is recorded apart and not counted as a run.
- `who-fp16-synthetic` is repeated twice more, unregistered, to check that identical runs give identical segments.
- Wall time and peak memory come from `/usr/bin/time -l`. The load and diarize times come from the runner's own output, which counts decoding inside the diarize time.

**Network.** Besides the weight download, the SDK sends a licence check to `events.desertant.com` when a model loads. It carries an install ID, the model and SDK versions, the platform and the process name, but no audio or results. As an offline check, one rerun of `who-fp16-synthetic` with weights present has `DAL_LICENSE_ENDPOINT` pointed at an unused local port. It passes if it completes with the same segments and leaves the model folder unchanged. This does not prove the machine had no network, only that inference needs neither download nor licence reply.

**References and evaluations.** No new listening is planned.

| Evaluation ID | Reference | Runs | When |
| --- | --- | --- | --- |
| `eval-who-synthetic` | `truth-synthetic`, from `review.py known` on the committed `reference/segments.json` | `who-fp16-synthetic`, `who-int8-synthetic`, `sortformer-synthetic` | now |
| `eval-who-two-track-call` | `tracks-two-track-call` (track activity) | `who-fp16-two-track-call`, `who-int8-two-track-call`, `sortformer-two-track-call` | now, provisional until session `check-two-track-call` is answered |
| `eval-who-part1`, `eval-who-part2` | `ref-full-calls-2026-10-29`, frozen from the existing session `full-calls-2026-10-29` | each recording's two Who runs and its Sortformer run | after the user answers that session |

```bash
python3 .agents/skills/meeting-experiment-review/scripts/review.py known "$MEETING_REVIEW_DATA" --recording synthetic --segments experiments/synthetic-call/reference/segments.json --id truth-synthetic
```

`full-calls-2026-10-29`'s clips were picked from Sortformer's turn changes. Scoring Who on them tests Who where Sortformer changes speaker, which may favour Sortformer. The report says so.

Until those references exist, the long calls report only label counts, each label's speaking time, and runtime and memory.

Mappings are fitted, as in the earlier experiments.

Clip selection: none new; the sessions above were picked earlier.

```json
{}
```

Skill code: commit `b5a03aedc46185e12c2ac142e72888aa556c53f2`; dataset snapshot `ad94e643592aa765539614b34c3f19096f18c747b86bbd65f583673a5024ca06` (from `dataset.py snapshot`). Restarts and reruns use this snapshot, not the current scripts.

Review session IDs: `check-two-track-call` and `full-calls-2026-10-29` (existing). Reference IDs: `truth-synthetic`, `tracks-two-track-call`, `ref-full-calls-2026-10-29`. Evaluation IDs: `eval-who-synthetic`, `eval-who-two-track-call`, `eval-who-part1`, `eval-who-part2`.

## Run the review

Run each from the repository root:

```bash
python3 .agents/skills/meeting-experiment-review/scripts/review.py serve "$MEETING_REVIEW_DATA" --session full-calls-2026-10-29 --port 8770
```

```bash
python3 .agents/skills/meeting-experiment-review/scripts/review.py serve "$MEETING_REVIEW_DATA" --session check-two-track-call --port 8771
```

Set `MEETING_REVIEW_DATA` to the private dataset first ([setup](../../README.md#setup)). Open the `http://127.0.0.1:…/?token=…` URL each one prints. Answers save as you go, and Ctrl-C stops the server. Click **Finish session** when done.

## Restart from scratch

If the private data for this experiment is lost:
1. Register the recordings again under the same IDs and rerun the commands in the plan.
2. Register the runs under the same IDs, and rebuild `truth-synthetic` from the committed segments.
3. Answer the two sessions again, using the skill code at the commit above (`git show <git-sha>:.agents/skills/meeting-experiment-review/scripts/…`) if the snapshot is lost too.

## Runtime and memory

## Results

| Measure | Result |
| --- | --- |
| Turns recovered | |
| Clips correct | |
| Excluded items | |
| Label mapping | |

**Metric limits.**

## Decision

## Open questions
