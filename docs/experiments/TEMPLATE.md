# YYYY-MM-DD: <topic>

**Status:** planned · runs in progress · review pending · complete

**Outcome:** the answer and the decision, in one to three sentences. Leave this as "pending" until there are results.

<!--
Write and commit this file before the first run, and fill in Results and the sections after it as the experiment goes.
Write for someone reading main, who has none of this experiment's history:
- Say what anything is relative to. Avoid "earlier", "new", "original" and "expanded" unless the sentence names the comparison.
- Name anything that isn't on main as such: a draft PR, an unmerged branch, a commit, or a file outside the repository.
- Never name people, quote transcripts, or give private paths.
Delete this comment and any line that doesn't apply.
-->

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/<name>/setup.sh` |
| Run everything | `experiments/<name>/run.sh <arguments>` |
| Check saved results without models | `<command>`, or "not possible" and why |

- **It needs:** inputs and tools the setup can't provide, such as a recording or a verified fixture folder.
- **It writes:** where the outputs go, and which file holds the measurements.
- **Takes about:** measured total, or the measured parts and what wasn't timed.
- **By hand:** every step the script can't do, in order. If there is none, say so.
- **Expect to differ:** what a rerun won't reproduce exactly, such as timings or model text.

To run a listening review, start it with this command from the repository root, with `MEETING_REVIEW_DATA` set to the private dataset ([setup](../../README.md#setup)). Open the `http://127.0.0.1:8770/?token=…` URL it prints; answers save as you go, and Ctrl-C stops the server. Click **Finish session** when done.

```bash
python3 .agents/skills/meeting-experiment-review/scripts/review.py serve "$MEETING_REVIEW_DATA" --session <session-id> --port 8770
```

If the private data is lost, rerun the entry point with the same IDs and rerun `pick_clips.py` with the config in the plan, using the skill code at the commit in the plan (`git show <git-sha>:.agents/skills/meeting-experiment-review/scripts/…`) if the snapshot is lost too. The same seed gives the same clips only if the runs reproduce the same segments and text; otherwise review the new plan before preparing a session.

## Question

What this experiment answers, in one or two sentences.

- **Decision it informs:** what will be chosen or ruled out, and by what result.
- **Expected result:** what we think will happen, and what result would change the decision.
- **Builds on:** the experiments and results relied on, linked. Say if any aren't on `main`.

## Plan

- **Input:** profile of the recording, never its name or path: number of people, languages, one track or several, online or in a room, duration, how it was captured. Dataset recording IDs and group.
- **Assumptions:** about the input, the models, and the machine (for example: a three-person online call on one mono track; models already cached; nothing else running during timed runs).

| Run ID | Model and pinned version | Settings |
| --- | --- | --- |
| | | |

Clip selection (`pick_clips.py` config; run IDs only, no paths):

```json
{}
```

Skill code: commit `<git-sha>`; dataset snapshot `<code-sha256>` (from `dataset.py snapshot`). Restarts and reruns use this snapshot, not the current scripts.

Review session ID: `<session-id>`. Reference ID: `ref-<session-id>`. Evaluation IDs: one per recording.

### Changes to the plan

Each change, its date and why, committed before acting on it. "None" if there were none. If the commits can't show whether a change came before or after the runs, say so, or leave this section out.

## Results

| Measure | Result |
| --- | --- |
| Turns recovered | |
| Clips correct | |
| Excluded items | |
| Label mapping | |

**Limits.** What these measures don't show.

## Runtime and memory

Per run, with any overlap noted. Say how they were measured.

## Decision

What was decided, and the result that decided it, or why the choice is cautious when the results don't favor one option.

## Open questions

## Where this ran

- **Code:** the commit each run used, and whether that commit is on `main`. If it isn't, say which PR or commit on `main` holds the same code.
- **Models and weights:** pinned revisions and digests not already in the plan.
- **Machine:** hardware, OS, and tool versions.
- **Kept outside the repository:** what is private or external, without its path.
