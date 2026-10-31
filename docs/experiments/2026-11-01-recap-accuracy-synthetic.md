# 2026-11-01: Recap accuracy on the synthetic call

**Status:** complete.

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

Each recap was one prompt of about 2,300 tokens, decoded in 77–99 s with a 6.71 GB MLX peak on the M2 Pro (16 GB). The `script` condition ran twice and gave byte-identical replies, so greedy decoding is repeatable on identical input.

## Results

Run `python3 experiments/recap-accuracy/score.py experiments/recap-accuracy/runs/<condition> experiments/recap-accuracy/matches/<condition>.json` from the repository root. The recaps and transcripts scored are in `experiments/recap-accuracy/runs/`.

| Measure | `sortformer` | `who` | `script` |
| --- | --- | --- | --- |
| Key items found (of 24) | 13 | 20 | 21 |
| Placed in an accepted section | 11 | 18 | 21 |
| Evidence covers the item | 13/13 | 18/20 | 21/21 |
| Recap items: correct / misplaced / wrong | 9 / 3 / 7 of 19 | 15 / 1 / 5 of 21 | 20 / 4 / 4 of 28 |
| Action owners right | 5/5 | 6/7 | 9/10 |
| Deadlines right | 5/5 | 7/7 | 9/10 |
| Missed | D5, D7, D9, D10, T4, T6, T8, T9, T11, P2, Q1 | D9, T4, T6, Q1 | D3, D5, T11 |

No recap had duplicates.

**Errors even with a perfect transcript (`script`).** These come from the summary model and prompt:
- **Answered questions listed as open (4):** whether the SDK upgrade affects Android, whether the crash hits every phone, whether mobile changes too, and whether the sprint fits. All of them were answered in the call.
- **Assignments listed as decisions (3), and an adopted idea listed as not decided (1):** lazy loading is under "Proposals (not decided)".
- **An owner given where the call names none:** the CI ticket.
- **A missed deadline:** "this week" for the SDK upgrade.

**Errors added in the pipeline recaps:**
- **Invented items:**
  - a ticket for the notification requirement (`who`);
  - a CI research task (`who`);
  - a question about QA's crash log (`who`);
  - a question about Speaker C finishing the CI work (`sortformer`).
- **Wrong facts:**
  - the Docker build deferred to next sprint (`sortformer`);
  - Speaker C rather than Speaker B helping with Android (`sortformer`);
  - the snapshot question attributed to the wrong speaker (`sortformer`).
- **Missed the most important items:**
  - Both missed Speaker A asking the PM (T4) and Speaker C's notification client work (T6).
  - `sortformer` also missed the demo date and scope (D9, D10). They appear in its topics but nowhere else.

**The recap swings with small changes to its input.**
- **The two pipeline transcripts are nearly the same:** identical ASR text, 95.1% and 95.8% speaker agreement, and the same names after merging. Their recaps still differ by 7 key items found and 2 wrong items.
- **One label change moved Sortformer's recap:**
  - The first Sortformer recap, written before its spare fourth label was merged, listed the demo date and scope as decisions.
  - The scored one, written after the merge, dropped both.
  - That earlier recap was replaced by `summarize --replace` and is not kept, so it is not scored here.
- **Conclusion:** one recap per condition can't separate the diarizers. Most of the difference is the summary model's sensitivity to small changes in the transcript.

**Metric limits.**
- Claude wrote the key and the verdicts, and there is one call with one sample per condition.
- Two answered questions (X6, X7) were added to the key after the `script` recap had been read. They decide 2 of its 4 wrong items and 1 of `sortformer`'s.
- Matching a recap item to a key item is a judgement, and so is calling an item misplaced rather than wrong. `matches/` records each verdict with a note.
- Topics are not scored. Several items missed in the scored sections appear in the topics.

## Decision

Fix the summary stage before tuning ASR or diarization for the recap.
- **Most errors are the summary stage's:**
  - Even a perfect transcript leaves 3 of 24 items missed and 8 of 28 recap items misplaced or wrong.
  - The pipeline recaps add invented items and lose up to 11 of 24 items.
  - Those losses are larger than the transcript's 4–5% speaker errors explain, and the recap swings between near-identical inputs.
- **Candidate fixes to measure next, on this call and its key:**
  - Prompt rules that an open question must still be unanswered at the end of the call, and that an assignment goes only in action items.
  - Separate passes per section, or a check pass that removes answered questions and items no transcript line supports.
  - Several samples per condition, to measure the swing rather than one draw.
- **Not decided here:** the diarizer for the recap. The Who recap scored better, but that difference is within the recap's swing. #25 still decides the diarizer on speaker accuracy.

## Open questions

- How much do the prompt changes above reduce errors on the `script` condition, and do they hold on the pipeline transcripts?
- How large is the recap's swing? Some small input changes that keep the meaning, such as renaming a speaker or moving one turn boundary, would measure it.
- Do the same error kinds appear on a real call? The private-recording review for #28 checks usefulness and omissions there.

## Follow-up: summary stage variants

**Status:** planned. This section was committed before any variant ran.

**Question.** Do stricter prompt rules, or a second pass that checks the draft against the whole transcript, cut the errors found above without losing items? And how much does a recap move when only the speaker names change?

**Variants** (in `pipeline.py`, selected by the summary stage's third argument):
- **v0:** the prompt scored above.
- **v1:** stricter rules:
  - read the whole call first, because later lines can answer earlier questions;
  - decisions hold agreed approaches, including adopted proposals, but not who-does-what;
  - an action item's owner is the person assigned or volunteering, and any stated deadline is copied;
  - proposals are only ideas never adopted;
  - open questions are only those still unanswered at the end;
  - invent no tasks, tickets or questions.
- **v2:** v1 plus a check prompt. It gets the whole transcript and v1's draft, and removes unsupported items and answered questions, moves misplaced items, fixes owners and deadlines, and adds missed decisions and tasks. This costs one more prompt.

The rules are written for meetings in general. They name no topic or item from this call, but they were written after reading its recaps, so this call can't show how they generalize. That is left to the private-recording review.

**Inputs:**

| Input | What it is |
| --- | --- |
| `script` | The script's text and speakers, as above |
| `script-relabeled` | The same script with the speaker names rotated (A is called Speaker C, B Speaker A, C Speaker B). Same meaning, different text. It measures how much a recap moves on a change that should not matter |
| `sortformer`, `who` | The two pipeline transcripts scored above (`runs/*/transcript.md`) |

**Runs.** `recap_variant.py <input> runs/<variant>-<input> <variant>`:
- v1 and v2 on all four inputs;
- v0 on `script-relabeled`.

The four v0 runs on the other inputs are the three scored above.

**Scoring.**
- The same `score.py` and key, with hand verdicts in `matches/<variant>-<input>.json` using the rules above. The key is frozen as committed.
- `score.py` maps relabeled owners back through `names.json`.
- I judge each recap knowing its variant, so a reader should spot-check `matches/`.

**Decision rule.** A variant replaces v0 in the pipeline if, summed over the four inputs:
- it finds at least as many key items;
- it has fewer wrong items;
- it moves less between `script` and `script-relabeled`.

If v1 and v2 both qualify, v2's extra prompt (about 90 s per recap) has to buy at least 3 fewer wrong items in total to be worth it.
