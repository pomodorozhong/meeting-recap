# 2026-11-02: recap facts and citations on the 17-recording synthetic collection

**Status:** complete

**Outcome:** Better transcripts alone didn't ensure better notes: on two calls, the recap stated 7 of 9 facts fully correctly with full Whisper + Sortformer, 6 of 9 with Turbo + Who, and 6 of 9 from the script's exact turns. Starting a transcript line at each Whisper segment removed the uncited items from the English audit call's recap and gave more correct facts with supporting citations, so it's offered as an option. The recap model and prompt don't change. This rests on 12 targeted facts from three calls, graded once by a grader who knew which version was which.

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/synthetic-call/collection_setup.sh` |
| Run everything | `experiments/synthetic-call/collection_run.sh "$FIXTURES" "$RESULTS"` |
| Rerun this summary's steps | `--step decode` on a new `RESULTS`, then `--step diarize`, because `recaps` and `replays` read their output; then `experiments/synthetic-call/collection_run.sh "$FIXTURES" "$RESULTS" --step recaps`, then `--step replays` |
| Check saved results without models | `uv run --project experiments/synthetic-call experiments/synthetic-call/collection_scores.py "$FIXTURES" "$RESULTS" > scores.json` |

- **It needs:** `FIXTURES`, the verified collection built by [`collection.py`](../../experiments/synthetic-call/README.md#seventeen-recording-collection), and `RESULTS`, a new absolute path outside Git. `recaps` needs the input digests from `decode`. `replays` needs the Turbo + Who recap runs from `recaps`, and the English training call's Turbo output from `decode` and Who output from `diarize`. A step started without them stops before running any model and names the missing file and the step that writes it.
- **It writes:** every model output under `RESULTS`, with the measurements in `RESULTS/scores.json`. This is one run shared by [several summaries](../../experiments/synthetic-call/README.md#compare-the-pipeline-on-this-collection), so the scorer needs every step's outputs. [The saved measurements](2026-11-02-synthetic-collection-results.json) are the committed copy.
- **Takes about:** 9 minutes for `recaps`, in the saved timings; `replays` wasn't timed. The whole run takes about 54 minutes of timed steps, and a full run on a new folder on 2026-11-06 took about 66 minutes with `turns` and `replays`.
- **By hand:** grading the recaps against the fixed checks in the plan. [Fact verdicts bound to output hashes](2026-11-02-synthetic-collection-recaps-judgments.json) holds this run's grades. Grade fresh outputs again, including their cited source lines, because changed text can't inherit an earlier judgment.
- **Expect to differ:** timings on any rerun, and possibly model text on another machine. On the original M2 Pro, rerunning the `replays` step on 2026-11-03 matched the saved words, transcripts and recaps byte for byte. The 2026-11-06 full run on a new folder also ran `recaps`: the text of all six recap summaries (three settings on each of onboarding and English audit) was byte-identical to the original run, and the recap checks were unchanged. The [other differences](../../experiments/synthetic-call/README.md#rerun-on-a-new-folder-2026-11-06) were timings, memory and file digests.

## Question

Do clean transcripts keep recap facts correct? Does a faster pipeline keep the same facts? Does finer transcript line structure improve citations?

- **Decision it informs:** whether to change the recap model or prompt, whether fast options need extra caution, and whether to offer per-segment lines.
- **Expected result:** cleaner input can help, but faster component times and readable Markdown don't guarantee preserved owners, dates or corrected decisions. A result of more valid timestamps alone wouldn't pass the citation test.
- **Builds on:** a [seven-recording trial](https://github.com/pomodorozhong/meeting-recap/blob/c714e05/docs/experiments/2026-11-01-synthetic-collection.md) in draft PR #31, which is **not on `main`**.

## Plan

- **Input:** two hash-verified mono fixtures from the collection at `4c8c2f0`: onboarding (four speakers, testing ownership) and English audit (one speaker, testing corrections). The citation test adds English training.
- **Assumptions:** one M2 Pro with 16 GB, serial local inference. Anonymous labels are mapped to the reference by maximum shared speaker time.

| Run ID | Input | Settings |
| --- | --- | --- |
| `pipeline` | Full Whisper + Sortformer | Qwen3.5 9B `8b2b98c0`, through the pipeline |
| `fast` | Turbo Q4 + Who | Same model and prompt |
| `exact` | The script's exact turns | Same model and prompt, summary stage only |

Each recap is scored full, partial, or absent or wrong on nine checks, committed before any recap result was recorded (see Changes to the plan):

- **Onboarding, turns 9, 10, 12, 14–16:** account test owner and time; documentation owner and time; test access restored; production access still separate and unapproved.
- **English audit, turns 2, 3, 7, 8/11, 10:** corrected adapter total; usable cable count; scale fault unresolved; corrected booking; delivery expected, not received.

Reopened questions and unsupported details are also counted.

### Changes to the plan

On the unmerged branch `codex/expanded-call-benchmark`, the nine checks were committed in `e5f17b3`, before `e64bfe5`, the first commit that recorded a recap result. Git shows when text was committed, not when a run happened, so this doesn't show that the checks came before the runs. Later edits changed vocabulary so the text reads against `main`, such as "earlier" to "the trial's". No threshold or rule changed. One check was reworded with the same meaning when results were recorded: "B's practice check by Thursday at ten" became "B responsible for the practice check, due Thursday 10:00".

Two comparisons were added during the experiment:

- **Turbo + Who:** committed in `168cca5`, before the first commit that recorded a recap result. It uses identical language settings, the same prompt and the same nine checks, with the default as comparator.
- **Per-segment lines (added after a result):** the Turbo + Who audit recap prompted this test. Onboarding is a second call checked afterward, and English training's three facts were committed with the citation test in `e64bfe5`, before its recap results were recorded in `0b61e1b`: final count of 18 verified (turns 7/8/18); A's checklist revision by Wednesday noon (21); B responsible for the practice check, due Thursday 10:00 (22). The option passes only if the audit has fewer uncited items and at least one more fact that is fully correct with supporting citations, and no fully correct fact is lost on any of the three calls.

On 2026-11-03, after the runs, this summary was split out of one write-up covering every question, so that each question has its own summary and decision. No result changed. Nothing was rerun for the split.

## Results

### End-to-end recaps

| Input | Full Whisper + Sortformer | Turbo + Who | Exact turns + identical recap model |
| --- | ---: | ---: | ---: |
| Onboarding (4 checks) | 2 full, 1 partial; 135.66 s | 2 full, 1 partial; 68.97 s | 3 full; 29.57 s |
| English audit (5 checks) | 5 full; 159.30 s | 4 full, 1 partial; 80.01 s | 3 full, 2 partial; 53.77 s |
| Full facts across the two calls | **7/9** | **6/9** | **6/9** |

Wall times in the first two columns start from audio; the exact column times only summarization from known turns. A correct value with a contradictory correction or a reopened final status earns partial credit. A check not counted as full or partial was absent or wrong.

- **Onboarding:** full Whisper + Sortformer stated both assignments. Turbo + Who merged speakers and lost the test owner, while recovering the separate production-access decision. All three omitted the successful test retry.
- **English audit:** full Whisper + Sortformer stated the facts but presented settled counts as still open. The exact-input recap misstated the superseded booking day and reopened receipt of the delivery. The Turbo + Who recap stated delivery had not arrived and also asked whether it had.
- **Citations:** the Turbo + Who audit recap had 37 invalid citations removed and 21 items left uncited. All the other recaps in this table had zero of either.
- **Language:** one full Whisper + Sortformer recap was in English despite a prompt requesting Traditional Chinese.

Two of the trial's claims need limits. Cleaner transcripts can help, but don't guarantee better notes. Two recaps can also take similar time and get similar scores while getting different facts right.

### Per-segment transcript lines

With identical Turbo words, Who labels and recap prompt, keeping Whisper segment boundaries gave the recap more precise lines to cite:

| Call | Transcript lines, merged → segmented | Uncited items | Fully correct facts | Fully correct with supporting citations |
| --- | ---: | ---: | ---: | ---: |
| English audit (5 checks) | 2 → 21 | 21 → 0 | 4 → 4 | 2 → 4 |
| Onboarding (4 checks) | 19 → 46 | 0 → 0 | 2 → 3 | 2 → 3 |
| English training (3 checks) | 22 → 48 | 0 → 0 | 2 → 2 | 2 → 2 |

The audit went from 37 invalid citations removed to zero. Onboarding recovered the successful retry with supporting evidence, but the merged speaker still caused a wrong owner. Neither training recap stated that 18 was the **verified final** count; both stated who was assigned what. Some segmented lines start in the same displayed second, so a timestamp may still be ambiguous.

The option met the pass rule set before the test, including on the training call, whose recap hadn't been generated yet. The command `run --asr turbo-q4 --diarizer who --language en --keep-asr-segments --no-summary` on the audit matched the graded segmented transcript byte for byte.

**Limits.** These checks look for specific facts anywhere in the recap, so they don't show how much else the recap got wrong. They were graded once on synthetic speech, by a grader who knew which version was which. The audit's own bad result prompted the citation test, so its improvement may be overstated. These are paired examples, not an estimate of general recap accuracy.

## Runtime and memory

Wall times are in the recap table, measured with `/usr/bin/time -l`, one inference process at a time on the M2 Pro with 16 GB, with the desktop in normal use. These are individual observations on this machine, not latency guarantees.

## Decision

Don't change the recap model or prompt. Offer separate timestamped lines per ASR segment for finer citations. Each recap item cites transcript lines. Before acting on an owner, date or decision, read the cited line. Nothing checks this automatically, and a cited line can carry a wrong speaker label. Fast options get no separate rule: read the cited lines for every recap. See decision 15.

## Open questions

Long meetings, real-room noise and accuracy against a listener-confirmed reference remain open. The next step is checking owners, decisions and citation support on the private listening reviews, before changing the default.

This run also compared action extraction on two further scripts, using frozen prompts from draft PR #31, which isn't on `main`. That comparison is left out of this summary because its claims belong with that draft's experiment. Its results and judgments are at [commit `d182e52`](https://github.com/pomodorozhong/meeting-recap/blob/d182e52/docs/experiments/2026-11-02-synthetic-collection-pipeline.md#action-recovery-and-evidence).

## Where this ran

- **Code:** the collection is the one merged in #32 (`4c8c2f0`). The runs used development commits based on it, before `--keep-asr-segments` merged in #35. The development commits are not on `main`. Replaying the per-segment commands on the pipeline code in `main` gave the results above.
- **Models and weights:** the revisions in the plan, and in [`pins.py`](../../experiments/pipelines/whisper-sortformer/pins.py).
- **Machine:** one M2 Pro with 16 GB, one inference process at a time.
- **Kept outside the repository:** raw calls, predictions and individual recaps, under benchmark ID `expanded-pipeline-20261102`. Public results contain counts and digests only.
