# 2026-11-01: Recap accuracy on the synthetic call

**Status:** planned.

## Question

How accurate is the pipeline's final recap, meaning its decisions, action items with owners and deadlines, proposals and open questions? How much of its error comes from the summary model itself, and how much from ASR and diarization upstream? Does `--diarizer who` change the recap compared with Sortformer?

## Goal and assumptions

- **Decision it informs:** what to fix first in the [whisper-sortformer pipeline](../../experiments/pipelines/whisper-sortformer/README.md) ([#28](https://github.com/pomodorozhong/meeting-recap/issues/28)).
  - If the recap of the script is wrong in the same ways as the pipeline's recaps, fix the summary stage (prompt, structure, or model) first.
  - If only the pipeline recaps are wrong, fix the transcript first.
  - If the Sortformer and Who recaps differ, that difference counts in the diarizer choice (#25).
- **Builds on:** the pipeline's [synthetic-call baseline](../../experiments/pipelines/whisper-sortformer/README.md#baseline-on-the-synthetic-call-2026-11-01). Transcript speaker agreement there was 95.1% with Sortformer and 95.8% with Who, and the recaps listed assignments as decisions.
- **Assumptions:**
  - The synthetic call's [script](../../experiments/synthetic-call/script.json) is the truth for what was decided and assigned.
  - The [answer key](../../experiments/recap-accuracy/key.json) was written from the script before any recap was scored.
  - Decoding is greedy, so one run per condition is representative. The script condition is run twice to check that.
- **Expected result:**
  - Owner and section errors also appear in the script condition. They come from the summary model and prompt, not the transcript.
  - The two pipeline recaps differ in wording more than in accuracy.

## Input

The synthetic call: 5:29, three generated voices, Taiwanese Mandarin with English terms, one track, seed 7 (`call_sha256` as in `experiments/synthetic-call/reference/manifest.json`). It isn't private, so everything here, including the recaps, can be public.

## Plan

| Condition | Transcript fed to the recap | Recap |
| --- | --- | --- |
| `sortformer` | Pipeline run with Sortformer. Its spare fourth label (2 characters) is merged into Speaker C in `speakers.json` | `summarize --replace` after the merge |
| `who` | Pipeline run with `--diarizer who` (three labels, no merge needed) | from `run` |
| `script` | The script's own text and speakers, one line per turn, timestamped from `reference/transcript.json` | `script_recap.py`, which runs the pipeline's `summary_stage.py` |

Every condition uses the pipeline's summary stage unchanged: Qwen3.5 9B 4-bit at `8b2b98c00a6b4d291155e4890773ca8f769aee53` through `mlx-lm` 0.32.2, greedy, thinking off.

**Scoring** ([`experiments/recap-accuracy/`](../../experiments/recap-accuracy/)):
- `key.json` lists 24 items that a correct recap holds, each with its script turns and the sections where it counts as correctly placed:
  - 10 decisions
  - 11 action items, with owners and deadlines, or null when the call states none
  - 2 proposals
  - 1 open question
- `key.json` also lists 5 questions the call answered. A recap that lists one of them as open has made an error.
- Each recap item gets a hand verdict in `matches/<condition>.json`:
  - **correct:** true, and in a section the key accepts for it.
  - **misplaced:** true, but in the wrong section, such as an assignment listed only as a decision.
  - **wrong:** contradicts the call, such as a wrong owner, an invented task, or an answered question listed as open.
  - **duplicate:** repeats an item already counted.
- `score.py` then reports:
  - key items found;
  - key items placed in an accepted section;
  - whether the cited timestamps cover the item's script turns;
  - recap items by verdict;
  - action owners right, checked against the key automatically;
  - deadlines right.
- Topics are not scored.

**Limits:**
- Claude wrote the key and made the hand verdicts. Read `matches/` to check them.
- One generated call can't represent real calls. The private-recording review for #28 judges usefulness and omissions on a real call.

## Runtime and memory

## Results

| Measure | `sortformer` | `who` | `script` |
| --- | --- | --- | --- |
| Key items found | | | |
| Placed in an accepted section | | | |
| Evidence covers the item | | | |
| Recap items: correct / misplaced / wrong / duplicate | | | |
| Action owners right | | | |
| Deadlines right | | | |

**Metric limits.**

## Decision

## Open questions
