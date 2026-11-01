# Review of the synthetic action experiments

**Status** Review complete. New inference experiments are designed, not run.

The measured ranking remains useful for these inputs. It does not establish that better transcription is the main route to reliable action items, that citations demonstrate grounding, or that the synthetic ranking transfers to ordinary meetings. Keep full Whisper/focused and Turbo/focused as comparators, not validated product choices.

This audit covers the [seven-recording matrix](2026-11-01-synthetic-collection.md), [ten-call action matrix](2026-11-01-action-evidence.md), their committed metrics and semantic judgments, the generation/extraction/scoring code at `cac52ea`, and saved inputs and outputs. No new model inference or listening judgment was used.

## The shared unproven assumption

**A script-derived answer key, recovered through a transcript and accompanied by citations, is a valid proxy for faithful recovery of useful commitments from a meeting.**

There are several unverified links in that assumption.

1. The generator actually speaks the intended script, including negations, task nouns and dates.
2. The task is identifiable from the recorded words. The meetings provide sufficient context, and one final task/owner/deadline interpretation is justified.
3. The extractor uses the decisive evidence, rather than recurring phrasing, likely tasks or a plausible completion of corrupted text. A supporting citation can be selected after the answer is guessed.
4. Our reference and grader distinguish correct actions from plausible ones consistently.
5. Those behaviors and model rankings survive different wording, voices, longer meetings and real conversation.

The experiments exercise parts of this chain but do not validate the chain. The original collection itself is a useful diagnostic instrument. Its size or a higher score cannot establish its validity. A related architectural assumption is that extracting outstanding actions from chunks retains enough information to resolve later corrections. An action list can discard a cancellation that must invalidate an earlier chunk's action.

## Findings and corrections

| Priority | Finding and evidence | Correction and test |
| --- | --- | --- |
| High | **Intended text is treated as spoken truth.** `generate.py` writes `transcript.json` directly from the requested text. Waveform hashes, level checks and matching durations establish provenance, not pronunciation. Both ASRs produce a long unrelated final line on the classroom-reservation call. This is a warning signal, not proof of a TTS defect. | First test reasoning with exact text. For audio, distinguish script agreement from independently established speech accuracy. Repeat synthesis with crossed voices/seeds, retain all outputs and disagreement strata. Model agreement must never certify the reference. |
| High | **Component attribution is confounded.** Exact/script versus audio changes words, punctuation, boundaries, timing and labels. Full/Turbo uses identical diarization intervals, but different word times alter attachment and displayed turns. In the menu call both ASRs move fragments across speaker boundaries differently. | Factor lexical content, speaker labels and boundaries separately on controlled transcripts. Compare full pipelines as systems, but do not describe their difference as a words-only effect. |
| High | **Supporting text does not prove causal dependence.** There are corrections in the corpus, but no matched case that changes only one decisive fact or removes it. | Paired factual changes, evidence removal, cancellation and completion must change the answer. Paraphrases and irrelevant additions must preserve it. Require both members of a pair to be correct. |
| High | **The grader sees the intended answer while judging corrupted evidence.** Hashing rows hides condition labels, not recognizable transcription artifacts. One author/grader supplied scripts, keys, judgments and interpretation. Replay verifies arithmetic and provenance, not semantic correctness. | Grade claim support against the complete input without the intended key first. Separately compare claims with the intended answer. Freeze field aliases and state rules, include deliberate wrong answers, and report ambiguous cases under both strict and permissive interpretations. An additional local-model judge is a sensitivity check, not ground truth. |
| High | **Only one whole-call negative control.** Within-call rejected tasks help, but do not measure false alarms across kinds of no-action meetings. | Use matched cancellation, completed-work, proposal and evidence-absent negatives. Report empty-call false-alarm rate separately from action precision/recall. |
| Medium | **Timestamp evidence is not a unique reference.** `pipeline.stamp` truncates to seconds. `score_actions.read_case` retrieves every line with that stamp. `accepted_items` converts selected line numbers back to those stamps, losing identity. The ticket call has two `00:00:13` lines in five conditions. | Use unique line IDs plus millisecond audio ranges in a new schema. Fail on ambiguous references. The current saved strict hits do not rely on the colliding stamp; this audit does not retroactively subtract hits. Include an explicit two-lines-in-one-second regression before future short-turn experiments. |
| Medium | **Verification was uncalibrated.** Six verifier invocations returned empty lists; four other conditions skipped inference. The filter removed all four true positives as well as five false positives. No known-good candidate was tested independently. | Test a verbatim supported candidate, then change only owner, date, recipient, supporting text or final state. Separate candidate acceptance from citation selection. Do not conclude verification in general is useless from this prompt's failure. |
| Medium | **The “focused” treatment bundles several changes.** It changes output scope, instructions about final state, evidence requirements and response length. The ordinary prompt does not give all the same state rules. | Treat this as a comparison of complete prompts. To attribute an effect to output scope, cross ordinary/action-only schemas with identical state/evidence rules in a new 2×2 test. |
| Medium | **70 cells are ten families, not 70 independent meetings.** Fourteen gold actions share context. The focused prompt's extra two hits occurred in one call. Full ASR won on three calls and tied on seven. | Report paired family-level outcomes, leave-one-family-out sensitivity and intervals clustered by base family. An illustrative two-sided sign test on the three non-tied ASR calls gives 0.25; the sample does not establish a stable population advantage. No retrospective significance claim is warranted. |
| Medium | **Selection and evaluation reuse the same set.** The verifier and full-ASR additions were designed after viewing outputs. Their preregistration prevents changing those runs silently, but does not make the set a fresh confirmation cohort. | Keep these results exploratory. Freeze development and holdout families before new inference; no tuning after holdout inspection. A revised prompt needs a new holdout. |
| Medium | **Short calls bypass meeting-scale failure modes.** New calls last about 17–31 seconds. Focused extraction explicitly rejects multiple chunks; normal recap merges chunk summaries without original transcript evidence. | Test controlled placement of commitment and later cancellation across chunk boundaries. Report unsupported length as a coverage limitation, never as a valid empty result. Compare an event-preserving representation only after freezing it. |
| Medium | **The strict score combines distinct failure modes.** Wrong intent, wrong speaker, missing date, wrong state and insufficient citation all become a failed action. Missing owner/date can be legitimate. | Keep strict utility as a primary outcome, but add intended-task correctness, transcript faithfulness, final-state correctness, field recovery, citation sufficiency and abstention. A truthful transcription of wrong synthesized speech differs from an extractor inventing a task. |
| Low | **Timing describes tiny files and fixed execution order.** Serial execution is appropriate; process startup/model load can dominate. Per-process peak is not whole-machine peak. | Report cold and warm process startup separately, end-to-end latency and steady throughput. Rotate condition order and time repeats on a longer fixed workload; record system pressure. Avoid multiplying a 20-second-call latency into a one-hour prediction. |

## What survives this review

- The frozen outputs and arithmetic support the reported 7/14 versus 4/14 strict action counts under this rubric. This audit does not replace those numbers.
- Turbo was faster and smaller on the measured ASR runs. Full Whisper recovered three extra actions on these ten calls.
- The current verifier is unusable as configured. A filter emitting nothing cannot earn meaningful precision by abstaining universally.
- Better lexical accuracy is a plausible explanation for some gains, but label repair changed only 3/60 lines and is too weak an intervention to rule out attribution failures elsewhere.
- These tests can proceed without user input. Synthetic checks cannot establish real-world usefulness, natural meeting prevalence or user-confirmed spoken truth. Those remain explicit limits, not gates blocking the unattended work.

## Next work

The [falsification plan](2026-11-01-action-grounding-plan.md) starts by validating the measurement and then challenges dependence on evidence, component attribution and transfer. The first exact-text fixtures and verifier controls are executable through [action-grounding](../../experiments/action-grounding/README.md). Existing measurements stay immutable; later results should link back here rather than rewrite the old verdicts.
