# 2026-11-28: four small language models as the recap model

**Status:** planned

**Outcome:** pending.

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/small-recap-models/setup.sh` |
| Run everything | `experiments/small-recap-models/run.sh "$FIXTURES" "$OUT"` |
| Check saved results without models | `uv run --project experiments/small-recap-models experiments/small-recap-models/scores.py "$OUT"` rebuilds the measurements from saved runs; [the saved measurements](2026-11-28-small-recap-models-results.json) are the committed copy |

- **It needs:** `FIXTURES`, the verified 17-recording collection built by [`collection.py`](../../experiments/synthetic-call/README.md#seventeen-recording-collection), and `OUT`, a new absolute path outside Git. The script refuses a folder inside Git.
- **It writes:** for each call, `OUT/<call>/lines.json` (the transcript lines every model reads) and `OUT/<call>/<model>/{notes.json,summary.md,run.json}`; `OUT/<model>.time` from `/usr/bin/time -l`; and the measurements in `OUT/scores.json`.
- **Takes about:** pending.
- **By hand:** grading each recap against the fixed checks below, saved as `OUT/judgments.json` in the format `scores.py` describes, then rerunning `scores.py`.
- **Expect to differ:** timings and memory on any rerun. Model text should repeat on the same machine and package versions, since decoding is greedy.

## Question

Can a model of 1.7 to 4 billion parameters write recaps as good as Qwen3.5 9B's, on the same prompt and transcripts, with less memory or time?

- **Decision it informs:** whether one of Gemma4 E2B, MiniCPM5 2B, LFM3-1.7B or Spark X2.6-4B replaces Qwen3.5 9B as the recap model (decision 7), is offered as a lighter option, or is ruled out. Related to #70, which asks the same question of Apple's on-device model.
- **Expected result:** the small models are faster and use much less memory, but lose facts, mainly owners and corrected values, and cite fewer supporting lines. A small model that matches Qwen on the checks with a third of its memory would change the default.
- **Builds on:** the [17-recording collection recap experiment](2026-11-02-synthetic-collection-recaps.md), whose `exact` arm gave Qwen3.5 9B the script's exact turns and scored 6 of 9 facts fully correct.

## Plan

- **Input:** the script's exact turns of two synthetic calls from the collection at `4c8c2f0`: onboarding (four speakers, Mandarin with English terms, testing ownership) and English audit (one speaker, testing corrected values). These are the inputs of the 2026-11-02 experiment's `exact` arm, built the same way: each turn labeled `Speaker <id>`, adjacent turns of one speaker joined, text converted to Traditional Chinese with OpenCC `s2tw`. Exact turns keep transcription and speaker errors out of the comparison.
- **Assumptions:** one M2 Pro with 16 GB, one model in memory at a time, each model in its own process; all models downloaded before the timed runs. Both calls fit in one prompt, so no merge step runs.

| Run ID | Model and pinned version | Settings |
| --- | --- | --- |
| `qwen3.5-9b` | `mlx-community/Qwen3.5-9B-4bit` at `8b2b98c0`, through mlx-lm 0.32.2 | The pipeline's recap prompt, greedy decoding, thinking off, 4,096-token output cap |
| `gemma4-e2b` | `lmstudio-community/gemma-4-E2B-it-MLX-4bit` at `31512dab`, through mlx-lm 0.32.2 | Same |
| `minicpm5-2b` | `openbmb/MiniCPM5-2B-MLX` at `c8c072db`, through mlx-lm 0.32.2 | Same |
| `lfm3-1.7b` | `LiquidAI/LFM3-1.7B-MLX-4bit` at `91f34088`, through mlx-vlm 0.8.1 | Same |
| `spark-x2.6-4b` | `mlx-community/Spark-X2.6-4B-OptiQ-4bit` at `6d83e911`, through mlx-lm 0.32.2 | Same |

All five run on MLX 0.32.4, the pipeline's version, as decision 7 requires. No mlx-lm release loads LFM3 yet, so it runs through mlx-vlm, the route its official MLX build documents. Spark X2.6's repository offers custom tokenizer code; it is never run (no `trust_remote_code`), and the tokenizer loads without it. Gemma4 E2B has no `mlx-community` build, so the LM Studio community build is used.

`qwen3.5-9b` is the baseline, rerun here on the same lines. Its `summary.md` is expected to match the 2026-11-02 `exact` recap byte for byte, which checks that the lines and prompt are the same.

**Checks.** Each recap is scored full, partial, or absent or wrong on the nine checks of the [2026-11-02 experiment](2026-11-02-synthetic-collection-recaps.md#plan), unchanged:

- **Onboarding:** account test owner and time; documentation owner and time; test access restored; production access still separate and unapproved.
- **English audit:** corrected adapter total; usable cable count; scale fault unresolved; corrected booking; delivery expected, not received.

For each check, the grader also records whether the lines the recap cites for that fact support it. Reopened settled questions and unsupported or garbled details are counted, as before. A recap whose reply isn't readable JSON scores zero on its call. One grader grades all five models' recaps in one pass, knowing which model wrote each, and the Qwen grades are compared with the 2026-11-02 grades of the same text as a consistency check.

**Decision rule, fixed before the runs.** A small model can **replace** Qwen only if, across both calls, it has at least as many facts fully correct with supporting citations as Qwen in this run, reopens no more settled questions, and has no unreadable reply. It can be **offered as a lighter option** if it is at most one such fact behind Qwen, has no unreadable reply, and peaks at under half of Qwen's memory. Otherwise it is ruled out for now. Either way, nine checks on two synthetic calls aren't enough to change the default alone: a model that passes goes on to the long real calls of #28 before decision 7 changes.

### Changes to the plan

None.

## Results

Pending.

**Limits.** Nine checks on two short synthetic calls, graded once by a grader who knew which model wrote each recap. Both calls fit in one prompt, so this says nothing about the merge step, where most long real calls fail (#28). The prompt was written and tuned for Qwen, which may favor it.

## Runtime and memory

Pending. Wall time of the recap call, the MLX peak, and the process's peak memory footprint from `/usr/bin/time -l`, one model process at a time.

## Decision

Pending.

## Open questions

## Where this ran

- **Code:** pending.
- **Models and weights:** the revisions in the plan.
- **Machine:** one M2 Pro with 16 GB.
- **Kept outside the repository:** the transcript lines, recaps and judgments with notes, in the private review dataset. Public results hold counts and digests only.
