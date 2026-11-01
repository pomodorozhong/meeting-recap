# Tests of grounding, attribution and synthetic transfer

**Status** Designed. Stage 1 inputs are materialized by committed code; no inference results yet. Stages 2–4 are protocol designs requiring their own frozen input manifests and implementation before execution.

## Question

Does an action extractor follow the decisive evidence, and do measured improvements survive changes that should preserve meaning? Which information loss actually explains failures? This follows the [audit](2026-11-01-action-evidence-review.md) and challenges the shared assumption that script-key agreement measures faithful, useful commitment recovery.

## Goal and assumptions

- **Decision informed** Whether to prioritize extraction/state tracking, lexical recovery, attribution, or the synthetic reference itself before running more model combinations.
- **Expected result** Clear explicit single-turn commitments should be recoverable. An evidence-grounded model should follow a changed owner/date/recipient, drop canceled/completed/unsupported commitments and ignore irrelevant details. Failure on exact text prioritizes extraction and evaluation before an ASR upgrade.
- **Machine** M2 Pro / 16 GB, cached models, serial offline inference. No external API, private recording or user listening session.
- **Reference** Controlled fictional text, never a user-confirmed audio transcript. Unknowns and ambiguity remain separate from false statements.
- **Freeze** Commit the plan, fixture source and prompts before inference. Preserve raw replies, input hashes, model/code/lockfile hashes and failed attempts. Run holdout once after development choices are frozen.

## Stage 0 — Validate the measurement before comparing models

Use unique source-line IDs internally and exact character or time ranges externally. Until a schema migration is implemented, Stage 1 deliberately uses distinct timestamps spaced ten seconds apart. The preparer records the one-to-one line mapping. It does not repair the existing pipeline's collision bug.

Before scoring new models, the evaluator must pass deterministic cases for a correct action, wrong owner, wrong date, wrong recipient, superseded task, duplicate prediction, unrelated-but-valid citation, same-second citation collision and empty-gold output. It must distinguish unsupported knowledge from an incorrect final state. Preserve line IDs through verification; never broaden a selected line to all lines in its second. Do not silently reuse old semantic judgments under a new schema.

Semantic grading has two passes. First inspect the full transcript and candidate with no script key, marking field support, counterevidence and final state. Then compare with the frozen intended action. Freeze accepted date and task paraphrases on development data before holdout. Record uncertainty, not a forced yes/no, and compute lower/upper scores for unresolved cases. An automated judge's output is a measured opinion; it cannot validate itself. No model receives `expected.json`.

## Stage 1 — Evidence interventions and verifier calibration

### Input and run IDs

Six fresh fictional Mandarin families in [families.json](../../experiments/action-grounding/families.json). Scanner, samples and slides are development families; badges, contracts and batteries are holdout. This split is by base family, including all transformations. The author knows the generated text; “holdout” means outputs unseen during prompt development, not independent authorship.

`extract/<family>/<variant>/<prompt>` identifies extraction runs. Ten variants per family produce 60 inputs and 120 runs across the two existing prompts. `verify/<family>/<control>` identifies 36 single-candidate verifier calls. The maximum initial matrix is 156 model invocations. Holdout contains 30 extraction inputs and 18 verifier controls. These templated probes are diagnostic controls, not six realistic meetings or independent evidence across all 60 variants.

| Variant | Intervention | Required relation to base |
| --- | --- | --- |
| base | Explicit commitment with object, recipient, owner and deadline | One fully supported action |
| owner | Change only the committing speaker B → C | Only owner changes |
| deadline | Change only the deadline | Only due changes |
| recipient | Change only the destination | Only recipient changes |
| cancelled | Append authoritative cancellation | No outstanding action |
| completed | Owner reports completion after commitment | No outstanding action |
| unsupported | Replace commitment and acceptance with undecided status | No outstanding action |
| conditional | Make commitment conditional and explicitly withhold approval | No unconditional action |
| irrelevant | Add a curtain-color observation | Same action and necessary support |
| paraphrase | Rephrase the commitment, preserving all fields | Same action and necessary support |

Citations may differ if they still support the same fields; textual equality of generated prose is not the metric. Both base and variant must be correct for a pair to pass. A consistently wrong answer cannot pass invariance. A consistently empty extractor cannot pass positive sensitivity. Conditional tasks are excluded only because this benchmark targets currently executable commitments; future conditional-task features need a separate schema.

Verifier controls give one candidate per call. The six controls per family are a correct verbatim candidate, wrong owner, wrong deadline, wrong recipient, absent supporting commitment and later cancellation. Measure acceptance of positives, rejection of each error class and complete evidence selection separately. A reject-all filter has zero positive acceptance and fails calibration. These easy positives test basic competence; passing them does not demonstrate detection of subtle errors.

### Models, prompts and commands

Use Qwen3.5-9B 4-bit `8b2b98c00a6b4d291155e4890773ca8f769aee53`, greedy decoding, thinking disabled, 4096 maximum output tokens. Baselines are `full_recap`, `ACTION_PROMPT` and `VERIFY_PROMPT` in the pipeline's `summary_stage.py` at source checkpoint `cac52ea`, with its locked dependencies. No prompt edits in this comparison. The original prompts' empty-array schema inconsistency remains a recorded baseline behavior; normalize only explicit empty lists as in the old experiment and report schema errors separately.

Preparation and example commands are in the [runner instructions](../../experiments/action-grounding/README.md). Use a fresh external output root. Commands pass only `lines.json` and, for verification, `candidates.json`. No new model download is needed. This initial pack does not yet implement a batch inference orchestrator or semantic scorer.

### Outcomes and decision gates

Primary outcomes are all-fields-and-evidence pair accuracy and false-positive rate on negative inputs. Report per-family tables, the three factual edit categories, the two invariant categories, and four negative categories. Also report raw JSON/schema failure rate, strict action precision/recall, and the fraction of intended fields that are supported by the input.

For each condition show successes/eligible pairs and clustered uncertainty by base family. With only three holdout families, intervals will be coarse; show all individual outcomes and do not interpret failure to reject as equivalence. Count transformations as repeated measures.

These are engineering gates, not confidence statements about real meetings. The simple verbatim positive must pass in all three development families before using that verifier in a larger pipeline. A counterfactual failure replicated in two independent development families is enough to prioritize fixing that behavior. Preserve failed baselines; a revised prompt becomes a separate registered arm. To advance an extractor to audio experiments require at least 90% pair accuracy and no outstanding actions on the simple negative controls in held-out fixtures. Report exact denominators and every exception even if the aggregate passes. Passing only qualifies the system for more difficult tests.

Serially complete development first (78 calls at most). Freeze any proposed repair and new scoring rules before holdout (78 calls for the two original extractors and original verifier). If development fails the gates, finish and report the original baseline matrix, but defer costly audio expansion. Limit each invocation to 120 seconds and the initial matrix to two wall-clock hours. Retain timeout/raw parse failures as failed cases with timing, never successful empty lists. Stop model work on sustained memory pressure; record incomplete cells instead of changing model settings mid-matrix.

## Stage 2 — Separate the information losses

**Hypothesis** Task-critical lexical corruption explains more missed actions than boundary errors or speaker attribution. This is not established by the old exact/audio contrast.

Freeze twelve new families with explicit, implicit and multi-turn commitments before inference. For each, create a fully crossed 2×2×2 transcript design: exact versus one critical lexical edit, correct versus one wrong speaker label, intact versus split/merged line boundaries. Choose edit positions in advance and retain all other characters and ordering. Lexical edits have their own revised transcript-truth key; the intended-meeting key stays separate. Split/merge operations must preserve token-level speakers; run a separate attachment-error condition when one displayed label necessarily changes their attribution. Do not call that operation a pure boundary edit.

Add two lexical controls per family: one equal-sized noncritical edit and restoration of the critical span. At one frozen extractor this gives 120 inputs (96 factorial + 24 lexical controls). Count effects per family and distinguish lost intended information from extraction failure given the visible text. Use unique line IDs, with character spans linking edited tokens to the original. Map speakers once using known identities, not an answer-dependent remapping.

For an audio followup, transcribe isolated known turns and rebuild the transcript with fixed true turn boundaries and identities. Compare both ASRs on these controlled inputs and on continuous audio separately. Isolated-turn recognition changes the ASR context; it is a diagnostic, not a pure estimate of the continuous pipeline's word error. Any alignment-based replacement must report unmappable/mixed spans rather than silently forcing alignment.

**Decision** If restoring critical words improves intended recovery consistently while the other factors do little, prioritize selective ASR repair. If the same correct words fail when split or attributed differently, prioritize evidence aggregation/attachment. If extraction fails with all factors exact, fix reasoning/state tracking. No average CER threshold substitutes for these outcomes.

## Stage 3 — Test script and acoustic transfer

**Hypothesis** The measured ranking depends little on the generator, preset voice or scripted phrasing.

Use the twelve Stage 2 meanings with two independently written realizations, one explicit and one natural with interruptions, references and distributed evidence. Freeze both keys before inference and report cases that require information outside the transcript as underdetermined. Never pretend a vague promise has a unique exact task key.

For each realization create two balanced preset-voice assignments and two seeds (7 and 19), giving 96 recordings. Rotate owner roles across voices. Run the two pinned ASRs with the same downstream extractor, serially. Exact-text versions isolate wording effects before synthesis. Seeds/voices are repeated measures within a meaning, not additional independent meetings. No filtering or resynthesis based on which candidate wins.

Keep script agreement as the primary synthetic reference measure. Use disagreement between already cached recognizers to flag questionable spans, without electing either one as truth. Report all recordings and a separately labeled unambiguous subset with the inclusion rule frozen in advance. Both ASRs agreeing still does not prove the TTS said the script. The same TTS with different voices does not establish cross-generator transfer; an independently pinned generator or independently annotated redistributable audio corpus would need a separate registered followup.

**Decision** If model ordering changes across voices, seeds or realizations, stop treating the original aggregate ranking as portable. Diagnose generator/wording sensitivity before adopting a default. Even stable synthetic results do not verify usefulness on private meetings; leave that question open while continuing unattended testing.

## Stage 4 — Test whether action lists preserve enough meeting state

**Hypothesis** Chunk-local action extraction plus merging can recover the final state of a longer conversation.

Freeze eight new scenario families containing a commitment, correction/reassignment and final cancellation or completion. Expand each with fixed irrelevant conversation into short, medium and long text budgets (about 1,000 / 6,500 / 18,000 characters). Place decisive changes either together or across the pipeline's actual 6,000-character chunk boundary, yielding 48 inputs. Move only irrelevant context when changing placement; record all line and chunk offsets. Measure context length in characters and tokens; do not label text length as minutes of recorded audio.

Compare the ordinary chunked pipeline with a separately frozen event-preserving extractor that retains proposals, acceptance, reassignment, cancellation and completion, together with source spans. The latter derives final outstanding actions only after processing the event sequence. This is an architectural candidate, not an implemented feature yet. The current focused extractor is a short-input comparator only; its rejection of multiple chunks is reported as unsupported coverage.

**Decision** Persistent resurfacing of canceled tasks across boundaries supports preserving state changes between chunks. If both representations fail at similar rates, inspect retrieval/context placement before claiming the event representation solves the problem. Report action-state accuracy and stale-action false positives along with total latency and peak process footprint.

## Runtime and memory

No new inference has run. Preparation is standard-library file generation. Existing short-call timings suggest Stage 1 is feasible locally, but its budget is a cap, not a measured estimate. Stages 2–4 need frozen runners, timing pilots and explicit run manifests before execution. Do not start the 96-recording expansion merely because Stage 1 files exist.

## Results and limits

Pending. The first deliverable is a reproducible falsification pack, not another accuracy claim. No listening session, reference confirmation or user feedback is required for the designed synthetic tests. Real-world usefulness and spoken-reference validity remain outside what this unattended suite can establish.
