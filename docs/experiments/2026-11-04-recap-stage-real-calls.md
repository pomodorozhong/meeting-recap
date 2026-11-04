# 2026-11-04: recap stage, then whole pipelines, on real calls

**Status:** planned. A screening step against Amie's output comes first; Stage A's decision and Stage B need hand-written answer keys. Stage B's pipelines and rule are fixed, and its recap setting follows from Stage A.

**Outcome:** pending

<!--
This file is the plan, committed before any run. Results and the sections after them are filled in as the experiment goes.
-->

## Reproduce

Not written yet. The pull request that adds the entry point (a script that reads a fixed labeled transcript and writes one recap per variant) must land before the first run.

## Question

Which full pipeline gives the most correct, correctly attributed and checkable meeting notes (decisions and action items) from a real call, within an M2 Pro with 16 GB and a reasonable wait?

- **Decision it informs:** whether the saved-audio pipeline's default recap model, prompt and chunking change, and whether Turbo + Who ever replaces full Whisper + Sortformer as the default. Both are decided on the final notes, not on transcript or speaker error alone.
- **Expected result:** the recap stage changes the notes more than the recognizer or diarizer does, and splitting a long transcript into chunks and merging their notes loses owners and items. If no recap variant beats a change to the prompt that shouldn't matter, the recap stage isn't the lever and Stage B decides alone.
- **Builds on:** the four [synthetic-collection summaries](2026-11-02-synthetic-collection-recaps.md) on `main` ([recognition](2026-11-02-synthetic-collection-recognition.md), [speakers](2026-11-02-synthetic-collection-speakers.md), [silence](2026-11-02-synthetic-collection-silence.md), recaps). They showed that component scores don't predict the notes (7/9, 6/9 and 6/9 facts for three inputs), that a diarizer putting two people under one label costs the recap the item's owner, and that the recap model and prompt were never varied. Tracked in #28 and #47.

## Why this replaces component ranking

- Turbo and full Whisper trade wins call by call, and Who and Sortformer trade wins by speaker count and overlap, so a component score doesn't say which pipeline gives better notes.
- The recap stage ran with one model, one prompt, greedy decoding and thinking off in every test.
- The synthetic calls were short, so most never used the chunk-and-merge path that long real calls need.
- The recap evidence is 12 facts from three calls, graded once by a grader who knew which version was which.

## Plan

- **Input:** real calls, 16 of them, mostly Mandarin, from 16 to 154 minutes, one mono track, with 2 to 7 speaker labels in Amie's transcript, which are its guesses and not counted speakers. They are in the private review dataset (the collection is described on the unmerged branch `feat/pipeline-baseline`, in `docs/amie-collection.md`). Nothing from them is in this repository. Results here say Speaker A/B/C and describe calls by length and kind.
- **Amie:** Amie is a commercial meeting-notes app. Its own transcript and summary for each call, copied from the app, are the reference in the screening step below. They are a reference, not ground truth: Amie's transcript is machine-made, its speaker labels are guesses, and whether the transcript was hand-corrected and which template the summary used are unknown. The export has no timestamps. Once hand-written keys exist, Amie is graded as one more candidate (B3).
- **Answer key:** written by the project owner from listening, for the calls the screening step flags, and before looking at any pipeline output for those calls other than the screening's. 8 to 12 items per call: decisions, action items with owner, task and due date, and things whose final value changed. Each item has the time it is said, so a grader can check it. Stage A's decision and Stage B need at least 6 keyed calls, with at least two over 60 minutes. The calls are chosen and written down before anyone grades a key item.
- **Grading:** outputs are coded and shuffled, so the project owner, who grades, doesn't know which pipeline made which. Each key item is marked full, partial, missing or wrong. The grader also counts unsupported statements (invented or wrong) and wrong-owner statements. The pipeline's own evidence check confirms that each cited timestamp matches a transcript line. Whether that line supports the claim is judged by the grader on a sample, by listening. Amie's summary has no timestamps, so it has no citation measure.
- **Assumptions:** models already cached; one inference process at a time; the desktop in normal use for timed runs.

### Screening against Amie

Added before any run, so the owner can learn something without writing keys for all 16 calls. Each Stage A variant's recap is compared with Amie's summary and transcript on all 16 calls, and the result is labeled exploratory.

- **What it can show:** large differences, such as a variant that drops half of what Amie's summary lists, that fails to produce valid notes, or that is far slower or heavier. The mechanical measures need no reference: whether the JSON parses, whether each cited timestamp matches a transcript line, time, and peak memory.
- **What it can't show:** which pipeline is correct. A variant that is right where Amie is wrong looks like a miss, and Amie's own output can't be scored against itself, so it is out of the screening comparison.
- **Not decided yet:** how agreement with Amie's summary is scored (a model judge or by hand). That method and its prompt must be fixed and committed before the first screening run.
- **Use of the result:** it picks which variants and which calls go forward to hand-written keys. It does not advance a variant by itself and it does not change a default.

### Stage A: the recap stage on fixed inputs

Each real call is run once through full Whisper with the declared language, Sortformer and word attachment, with transcript lines split per Whisper segment. That labeled transcript is saved and every variant reads the same file, so any difference comes from the recap alone. Today's recap is Qwen3.5-9B 4-bit through MLX. It sends the model one prompt per 6,000-character chunk of the transcript and, when there is more than one chunk, a second prompt that merges the notes. It picks the most likely next word every time (greedy decoding), and the model's step-by-step reasoning mode (thinking) is off.

Variants change one thing from the baseline, in order of expected effect. They are not a grid.

| Run ID | Change from baseline | Why |
| --- | --- | --- |
| A0 | None: today's recap | Baseline |
| A0-noise | A change that shouldn't matter: reordered JSON keys in the prompt | Greedy decoding repeats exactly, so rerunning measures nothing. This measures the noise floor instead: how much the notes move for a trivial change |
| A1 | Whole transcript in one pass instead of chunk and merge | The merge may drop owners and items. Calls too long for the model's context and 16 GB are reported as not run, not shortened |
| A2 | Thinking on | Earlier errors reopened settled facts and misread corrections |
| A3 | Rewritten prompt: owner only when clear (otherwise "unknown"), a later value replaces an earlier one, output language stated | Earlier errors were wrong owners and a recap in the wrong language |
| A4 | Other MLX recap models whose peak memory stays under 12 GB, measured with the recap stage's recorded MLX peak. A model that goes over is reported as not run | The model was never varied. The candidates and their pinned revisions are added to this table before the first A4 run |
| A5 | The winners of A1 to A4 together | Confirms they combine |

Controls:

- **C1:** Amie's transcript through the baseline recap, to separate its transcript quality from its summarizer.
- **C2:** the synthetic calls' exact turns through each variant, where the true transcript is known.

For the decision, a variant advances only if it beats A0 on key items fully correct with the right owner by more than A0-noise's spread, pooled over the keyed real calls, with no more wrong or unsupported statements. A tie goes to the cheaper setting.

### Stage B: whole pipelines

With the recap setting that won Stage A, compare end to end on the same keyed calls, with the same answer keys, blind grading and pass rule as Stage A, plus wall time and peak memory per call.

| Run ID | Pipeline |
| --- | --- |
| B1 | Full Whisper + Sortformer with the declared language and word attachment (the current default) |
| B2 | Turbo + Who (the fast option) |
| B3 | Amie's own transcript and summary (the same outputs as C1's input, graded as a finished product against the hand-written keys, not against itself) |
| B4 | Added only if Stage A shows owner errors come from merged speakers: B1 with a speaker-merge guard, described in the table before it runs |

What is fixed now, so Stage B isn't redesigned after seeing Stage A:

- the three pipelines above, the keyed calls and their answer keys, the grading steps, and the pass rule, which is Stage A's rule with "baseline" replaced by B1;
- B1 and B2 use whichever recap setting won Stage A, so they differ only in recognizer and diarizer.

What Stage A's result sets: the recap setting, and whether B4 exists. Both are written into this section as a dated change, committed before any Stage B run.

### What Stage A leaves for Stage B

Stage A is not finished until each of these is recorded here or in the private dataset:

- the recap setting that won, with its run ID, model revision and prompt text, committed as code;
- the saved labeled transcript for every keyed call, with its hash, so Stage B reuses it for B1;
- the noise floor from A0-noise, as a number of key items;
- the screening results against Amie, with the agreement method and prompt, and which variants and calls they sent forward;
- the answer keys and the shuffled-code mapping for grading, kept private, plus which calls were keyed and why they were chosen;
- the per-call time and peak memory for the baseline and the winner;
- any call that didn't fit a variant (A1 especially) and was reported as not run.

### What this leaves out

The digital-silence pause split, Breeze, the other diarizers, and the action-recovery benchmark in draft PR #31 (not on `main`) are not re-tested here.

### Changes to the plan

- **2026-11-04, before any run, while draft PR #59 was open:** added the screening step against Amie, made Amie the reference in screening and a candidate only against hand-written keys, moved the answer keys to the calls screening flags, and set A4's limit to 12 GB peak memory instead of "fits in 16 GB with room to spare". The project owner asked to use Amie's output as ground truth for now; the plan keeps it a reference because a machine-made transcript and summary can't tell us which notes are correct.

## Results

Pending.

**Limits.** To be filled in. Known already: the keys are written by one person for a small set of calls, Amie's settings are unknown, and nothing here covers a call in a language or room outside this set.

## Runtime and memory

Pending. Per run, from `/usr/bin/time -l` and the recap stage's recorded peak MLX memory.

## Decision

Pending.

## Open questions

- Which MLX recap models stay under 12 GB peak memory? A4 can't start without pinned candidates.
- How long a call fits in one pass (A1) with the chosen model and prompt?
- How is agreement with Amie's summary scored in the screening step?
- How many calls can be keyed by hand? The decision needs at least 6.

## Where this ran

Pending.

- **Kept outside the repository:** the recordings, Amie's exports, the answer keys, the grading and every recap output.
