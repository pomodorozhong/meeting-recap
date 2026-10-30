# 2026-10-30: Who against Sortformer

**Status:** review pending. Runs and the synthetic and two-track scores are done; the long calls wait for session `full-calls-2026-10-29`, and the two-track score for `check-two-track-call`.

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

Runs were timed with `/usr/bin/time -l`, one at a time, with nothing else running.
- **Weights:** both were already downloaded. The first load of each variant, which included the download and the Core ML preparation, took 37 s for fp16 and 44 s for int8. Later loads took 0.3–2.5 s.
- **Sortformer:** the synthetic run is new. The other Sortformer rows come from the runs already registered, which were measured the same way.

| Recording | Who fp16: wall, diarize, peak footprint | Who int8 | Sortformer: wall, peak |
| --- | --- | --- | --- |
| Synthetic, 5:30 | 3.2 s, 0.7 s, 285 MB | 3.0 s, 0.7 s, 296 MB | 140 s, 968 MB RSS / 750 MB footprint |
| Two-track call, 48:30 | 6.4 s, 6.0 s, 446 MB | 8.3 s, 6.0 s, 463 MB | 1192 s, 1209 MB footprint |
| 22:23 part | 5.4 s, 3.0 s, 372 MB | 5.2 s, 2.9 s, 371 MB | 721 s, 1061 MB RSS |
| 64:49 part | 10.7 s, 8.3 s, 522 MB | 10.2 s, 7.9 s, 520 MB | 1825 s, 1035 MB RSS |

Who ran about 100–450 times faster than real time, depending on how much of each run the load took. That is 45–185 times faster than Sortformer, with about half its memory.

**Repeats.** Two more fp16 runs on the synthetic call gave byte-identical segments.

**Offline check.** The fp16 rerun with the licence endpoint unreachable passed. It gave the same segments and left the model folder's files byte-identical.

**SDK quirk.** The runner's `model_was_downloaded` field, from the SDK's `isDownloaded()`, was false on some runs whose weights were present. Do not rely on it.

## Results

Scores are speaker-order LCS on the reference clips, with fitted mappings (one Who label per person on both recordings).

| Recording (reference) | Who fp16 | Who int8 | Sortformer |
| --- | --- | --- | --- |
| Synthetic, `truth-synthetic` (known turns) | 64/72 turns, 6/10 clips | 64/72, 6/10 | 67/72, 7/10 |
| Two-track call, `tracks-two-track-call` (track activity, provisional) | 516/629, 33/86 | 517/629, 32/86 | 527/629, 38/86 |

**Excluded items:** 0.

**Two-track call.**
- 18 clips are correct in both runs, 15 only in Who's, 20 only in Sortformer's, and 33 in neither. The two models fail on different clips, so the gap is not one systematic failure.
- Sortformer scores 527/38 here against the earlier summary's 528/39. That evaluation used an older skill snapshot from before the scoring fixes in #23; this one rescored Sortformer's registered run under the current snapshot.

**Synthetic call.**
- Who misses the same two clips as Sortformer, each with one short reply dropped.
- Who also gives one of Speaker B's turns to Speaker A, and misses all three of Speaker B's short turns near the end. Sortformer gets that last clip wrong differently: it gives one Speaker C turn a fourth label.

**Long calls, not scored yet.** Neither long call has a reference yet, so only labels can be compared:
- On both three-person parts, both models give three main labels and a fourth minor one. Who's minor label holds 13.6 s on the 22:23 part and 7.4 s on the 64:49 part. Sortformer's holds 24.1 s and 13.8 s.
- On the two-person call, Who gives three minor labels (12.4 s, 1.7 s and 1.6 s; int8 adds a fourth at 1.7 s). Sortformer gives two (3.4 s and 0.7 s).
- Who labels more speech overall: 758 s on the 22:23 part against Sortformer's 635 s. Whether that is speech Sortformer misses or noise has not been heard.

**Metric limits.**
- This is speaker order on selected clips: not DER, not transcript accuracy, and not an error rate for whole recordings.
- The two-track reference is track activity whose listening check is pending.
- The synthetic call has generated voices, so it is not a stand-in for real calls.
- Fitted mappings flatter every run equally.

## Decision

Provisional: keep Sortformer as the pipeline's diarizer, and keep Who as an optional alternative.
- **Quality:** Who is within 5% of Sortformer's turns on both scored recordings (4.5% fewer on the synthetic call, 2.1% fewer on the two-track call), but below it on both. That fails this plan's bar for replacing Sortformer and passes its bar for an alternative.
- **Speed and memory:** Who's are the strongest reason to keep it. It diarizes an hour in about 10 s, where Sortformer takes 30 minutes, so it could label speakers during or right after a call. Sortformer's place would be a later, slower pass.
- **int8 and fp16:** they score within one turn of each other at the same speed. If Who is used, the 42 MB int8 download is enough.

The decision is final once the long calls are scored.

## Open questions

- **Long calls:** on the two three-person parts, does Who keep the three voices apart once session `full-calls-2026-10-29` is answered (`eval-who-part1`, `eval-who-part2`)? And whose voice does the fourth minor label hold, for each model?
- **Two-track reference:** do the two-track scores hold once session `check-two-track-call` confirms the track activity? If the reference changes, rerun the evaluation under a new ID.
- **Minor labels:** does Who's minor-label speech carry real speech, such as laughter, which its model card says may get its own label, or is it noise?
- **Licensing:** what do the source-available licence and its scale threshold mean for shipping Who in `app/`? Its licence check sends an install ID from every install.
