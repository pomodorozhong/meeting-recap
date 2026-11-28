# 2026-11-06: per-segment lines with full Whisper + Sortformer

**Status:** review pending

**Outcome:** pending. The recaps are written and waiting for hand grading; only what can be counted without grading is below.

## Reproduce

This test uses the same run and the same grading round as [the recognizer and diarizer comparison](2026-11-06-recap-recognizer-vs-diarizer.md), so its Reproduce steps are that summary's. The setting this test adds is `whisper-sortformer-segments`.

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/synthetic-call/collection_setup.sh` |
| Run everything up to the hand grading | `uv run --project experiments/synthetic-call experiments/synthetic-call/collection_recap_pairs.py "$FIXTURES" "$PAIRS"` |
| Count the grades once filled in | `uv run --project experiments/synthetic-call experiments/synthetic-call/collection_recap_pairs.py "$FIXTURES" "$PAIRS" --report` |

- **It needs:** `FIXTURES` and a new `PAIRS` folder, as in the other summary.
- **It writes:** the folder for each call and setting, including `whisper-sortformer-segments`, and the shared grading sheets. A verdicts file committed after grading will hold this test's grades.
- **Takes about:** 7.7 minutes for its three runs with the flag, and 8.0 minutes for its three runs without it, inside the 32 minutes of the shared batch (pipeline run totals added).
- **By hand:** the shared grading round. Nothing separate.
- **Expect to differ:** timings, and possibly model text on another machine.

## Question

Does `--keep-asr-segments`, which starts a transcript line at every Whisper segment, help the pipeline's defaults (full Whisper + Sortformer) as it helped Turbo + Who?

[The recap facts experiment](2026-11-02-synthetic-collection-recaps.md) tested the flag only with Turbo + Who, where it removed the English audit recap's 21 uncited items and 37 invalid citations. The flag isn't limited to that pair. The recaps from full Whisper + Sortformer in that experiment had no uncited items on the two calls checked, so there may be nothing for the flag to fix with the defaults.

- **Decision it informs:** whether to say in the flag's documentation that it also helps the defaults, or that it doesn't.
- **Expected result:** little or no change, because the problem the flag fixed (uncited items) didn't appear with the defaults. A change in the number of facts supported by citations would be the only reason to document a benefit.
- **Builds on:** [the recap facts experiment](2026-11-02-synthetic-collection-recaps.md) and its decision 15.

## Plan

- **Input:** the same three generated calls as the other summary: `onboarding`, `english-audit` and `english-training`.
- **Assumptions:** as in the other summary.

| Setting | Recognizer | Diarizer | Command options |
| --- | --- | --- | --- |
| `whisper-sortformer` | full Whisper | Sortformer | none |
| `whisper-sortformer-segments` | full Whisper | Sortformer | `--keep-asr-segments` |

The comparison uses the same recap model, prompt and 12 fact checks as the recap facts experiment, and the grading terms defined in the other summary.

**Pass rule, set before the runs.** The flag helps the defaults if all three hold: (1) on every call where the setting without the flag has uncited items, the setting with the flag has fewer; (2) on at least one call the setting with the flag has more facts that are fully correct with supporting citations; and (3) no fact that is fully correct without the flag is lost with it on any call. This is the pass rule of the earlier Turbo + Who test, adapted: that rule required fewer uncited items on the audit, and here the audit may have none to remove. If the setting without the flag has no uncited items on any call and the flag doesn't raise the supported-fact count on any call, the documentation says the defaults have nothing for the flag to improve.

### Changes to the plan

None.

## Results

The batch ran on 2026-11-06. The recaps are not graded yet, so the pass rule can't be applied.

**What can be counted without grading.** A **line** is one transcript line the recap can cite. An **uncited item** is a recap item with no valid cited line, and an **invalid citation** is one the pipeline removed because it pointed at no transcript line. Lower is better for both.

| Call | Setting | Transcript lines | Uncited items | Invalid citations removed |
| --- | --- | ---: | ---: | ---: |
| Onboarding | without the flag | 16 | 0 | 0 |
| Onboarding | with `--keep-asr-segments` | 34 | 0 | 0 |
| English audit | without the flag | 2 | 0 | 0 |
| English audit | with `--keep-asr-segments` | 39 | 0 | 0 |
| English training | without the flag | 22 | 0 | 0 |
| English training | with `--keep-asr-segments` | 54 | 0 | 0 |

The flag more than doubled the lines on onboarding and English training and gave the audit 39 lines instead of 2. No setting has uncited items or invalid citations, with or without the flag. So rule 1 of the pass rule has nothing to apply to on these three calls, and the flag can only pass through rule 2: more facts fully correct with supporting citations on at least one call, graded by hand.

**Waiting on grading.** Whether the flag changes how many of the 12 facts are fully correct with supporting citations, and whether it loses any. The result and the wording for the flag's documentation go here after grading.
