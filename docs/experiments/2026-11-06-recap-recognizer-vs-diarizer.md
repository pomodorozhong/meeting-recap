# 2026-11-06: which part of Turbo + Who changed the recap facts

**Status:** review pending

**Outcome:** pending. The 12 recaps are written and waiting for hand grading; only what can be counted without grading is below.

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/synthetic-call/collection_setup.sh` |
| Run everything up to the hand grading | `uv run --project experiments/synthetic-call experiments/synthetic-call/collection_recap_pairs.py "$FIXTURES" "$PAIRS"` |
| Count the grades once filled in | `uv run --project experiments/synthetic-call experiments/synthetic-call/collection_recap_pairs.py "$FIXTURES" "$PAIRS" --report` |

- **It needs:** `FIXTURES`, the verified collection built by [`collection.py`](../../experiments/synthetic-call/README.md#seventeen-recording-collection), and `PAIRS`, a new absolute path outside Git. The script is shared with the test of `--keep-asr-segments` with the defaults (issue #50), which uses the same run and the same grading round.
- **It writes:** one pipeline output folder per call and setting under `PAIRS`, plus a grading sheet for each call whose recaps are labeled by letter, the key to those letters (`key.json`), and an empty `grades.json`. `--report` writes `report.json` with the counts and, in a verdicts file committed after grading, the grades bound to the hash of each recap.
- **Takes about:** 32 minutes for the 15 runs of the shared batch (the pipeline's own run totals added; they ranged from 48 to 202 s).
- **By hand:** read each lettered recap in `PAIRS/grading/<call>.md`, fill in `grades.json` for the 12 checks, then run `--report`. The sheet doesn't say which setting made a recap, but the number of transcript lines can give it away, so the grading is blinded only in part.
- **Expect to differ:** timings, and possibly model text on another machine. On the same machine and code, rerunning a setting that was run before (full Whisper + Sortformer and Turbo + Who on two calls) should give byte-identical text, because decoding is greedy.

## Question

When Turbo + Who produced worse recaps than full Whisper + Sortformer, was it the recognizer (Turbo instead of full Whisper) or the diarizer (Who instead of Sortformer)?

A **recognizer** turns speech into words and times. A **diarizer** decides who spoke when, and Who is faster but sometimes merges two speakers under one label. [The recap comparison](2026-11-02-synthetic-collection-recaps.md) changed both at once, so it can't say which change caused a difference. For example, on the onboarding call the Turbo + Who recap lost who owned the account test after two speakers were merged, but the recap's other differences can't be assigned to either part.

- **Decision it informs:** whether Turbo with Sortformer is safe to offer as a recap input beside the default, and whether the caution about Turbo + Who belongs to Turbo or to Who.
- **Expected result:** the onboarding owner error follows Who, because Who merged speakers on that call and the recognizer doesn't assign speakers. Nothing else is predicted. No result would make us rule out Turbo, since this checks 12 facts on three calls.
- **Builds on:** [the recap facts experiment](2026-11-02-synthetic-collection-recaps.md), whose model, prompt and fact checks this reuses unchanged.

## Plan

- **Input:** three generated calls from the 17-recording synthetic collection (`onboarding`: Mandarin with English terms, four speakers; `english-audit`: English, one speaker; `english-training`: English, two speakers). No real recording is used.
- **Assumptions:** one M2 Pro with 16 GB, serial local inference, models already cached, nothing else running.
- **Recap model and prompt:** unchanged from the recap facts experiment (Qwen3.5 9B, pinned in [`pins.py`](../../experiments/pipelines/whisper-sortformer/pins.py)), with the call's spoken language declared.

| Setting | Recognizer | Diarizer | Command options |
| --- | --- | --- | --- |
| `whisper-sortformer` | full Whisper | Sortformer | none (the pipeline's defaults) |
| `turbo-sortformer` | Turbo Q4 | Sortformer | `--asr turbo-q4` |
| `whisper-who` | full Whisper | Who | `--diarizer who` |
| `turbo-who` | Turbo Q4 | Who | `--asr turbo-q4 --diarizer who` |

All four settings are run again on all three calls in one batch so that the code, models and machine are the same for each. Two of them (full Whisper + Sortformer and Turbo + Who on onboarding and English audit) were graded in the recap facts experiment, and their text should repeat byte for byte.

**The 12 fact checks** are the ones from the recap facts experiment: four on onboarding, five on English audit and three on English training, listed in [`recap-checks.json`](../../experiments/synthetic-call/reference/recap-checks.json). Each recap is graded **full**, **partial** or **absent or wrong** on each check, and for each check whether a line the recap cites supports it. A fact is **fully correct with supporting citations** when it is graded full and a cited line supports it. Also counted: whether the recap reopens a question the call settled, whether it contains unsupported or garbled detail, and the **uncited items** the pipeline reports (recap items left with no valid cited line).

**What would count as an effect.** Graded once, by one person, on 12 facts, a difference of one or two facts between two settings is within what one regrading could change, so it won't be called an effect. The summary reports counts and the facts that moved, per call, and attributes a difference to the recognizer or the diarizer only when the two settings that share the other part show it in the same direction on the same call.

### Changes to the plan

None.

## Results

The batch ran on 2026-11-06 and wrote all 12 recaps for these four settings. They are not graded yet, so there are no fact counts, and the question above is open.

**Repeats.** The four settings that were graded in the recap facts experiment (full Whisper + Sortformer and Turbo + Who, on onboarding and English audit) produced transcripts and recaps that match the saved ones byte for byte. Turbo + Who on English training matches the saved merged-lines recap too.

**What can be counted without grading.** A **line** is one transcript line the recap can cite. An **uncited item** is a recap item with no valid cited line, and an **invalid citation** is a citation the pipeline removed because it pointed at no transcript line. Lower is better for both.

| Call | Setting | Transcript lines | Uncited items | Invalid citations removed | Run seconds |
| --- | --- | ---: | ---: | ---: | ---: |
| Onboarding | full Whisper + Sortformer | 16 | 0 | 0 | 146 |
| Onboarding | Turbo + Sortformer | 17 | 0 | 0 | 108 |
| Onboarding | full Whisper + Who | 19 | 0 | 0 | 95 |
| Onboarding | Turbo + Who | 19 | 0 | 0 | 48 |
| English audit | full Whisper + Sortformer | 2 | 0 | 0 | 157 |
| English audit | Turbo + Sortformer | 2 | 21 | 37 | 165 |
| English audit | full Whisper + Who | 2 | 0 | 0 | 70 |
| English audit | Turbo + Who | 2 | 21 | 37 | 78 |
| English training | full Whisper + Sortformer | 22 | 0 | 0 | 174 |
| English training | Turbo + Sortformer | 22 | 0 | 0 | 202 |
| English training | full Whisper + Who | 22 | 0 | 0 | 131 |
| English training | Turbo + Who | 22 | 0 | 0 | 92 |

On English audit, which has one speaker, the diarizer made no difference: each recognizer gave the same recap text with Sortformer and with Who. The 21 uncited items and 37 invalid citations appear with Turbo and not with full Whisper, whichever diarizer is used. That is a property of Turbo's transcript on this call, not of Who. This summary doesn't establish why, because both recognizers' transcripts have two lines.

Run seconds come from one run of each setting and include loading models, so they can't rank the settings precisely.

**Waiting on grading.** For each recap: the 12 facts, which cited lines support them, and the two flags. Counts and the effect on the question go here after grading.
