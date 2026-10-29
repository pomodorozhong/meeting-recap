# YYYY-MM-DD: <topic>

**Status:** planned · runs in progress · review pending · complete

Write and commit this file before the first run. Fill in the results sections as the experiment goes; nothing here may name people, quote transcripts, or give private paths.

## Question

What this experiment answers, in one or two sentences.

## Goal and assumptions

- **Decision it informs:** what will be chosen or ruled out, and by what result.
- **Builds on:** earlier experiments and the results relied on, linked.
- **Assumptions:** about the input, the models, and the machine (for example: a three-person online call on one mono track; models already cached; nothing else running during timed runs).
- **Expected result:** what we think will happen, and what result would change the decision.

## Input

Profile of the recording, never its name or path: number of people, languages, one track or several, online or in a room, duration, how it was captured. Dataset recording IDs and group.

## Plan

| Run ID | Model and pinned version | Settings | Command |
| --- | --- | --- | --- |
| | | | |

Clip selection (`pick_clips.py` config; run IDs only, no paths):

```json
{}
```

Review session ID: `<session-id>`. Reference ID: `ref-<session-id>`. Evaluation IDs: one per recording.

## Run the review

```bash
python3 .agents/skills/meeting-experiment-review/scripts/review.py serve "$MEETING_REVIEW_DATA" --session <session-id> --port 8770
```

Run from the repository root with `MEETING_REVIEW_DATA` set to the private dataset. Open the `http://127.0.0.1:8770/?token=…` URL it prints; answers save as you go, and Ctrl-C stops the server. Click **Finish session** when done.

## Restart from scratch

If the private data for this experiment is lost: register the recordings again under the same IDs, rerun the commands in the plan, register the runs under the same IDs, and rerun `pick_clips.py` with the config above. The same seed gives the same clips only if the runs reproduce the same segments and text; otherwise review the new plan before preparing the session.

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
