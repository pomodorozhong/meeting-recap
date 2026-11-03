---
name: experiment-writing
description: Draft, revise, or review experiment summaries and the decisions they support, so a reader who hasn't seen the experiment can follow what was tested, what the numbers mean, and what the result can't show. Use for files in docs/experiments/, entries in docs/decisions.md, and READMEs that report results. Routine code changes, PR descriptions, and chat replies are outside its default scope.
---

# Experiment writing

Help someone arriving directly at a summary understand what was asked, what happened, and what to do with the result.

## Workflow

1. Read [writing-principles.md](references/writing-principles.md) for tone, terms, pacing and evidence. It comes from the `explanatory-writing` skill in the author's `rabbit-holes` repository, so its examples aren't about this project.
2. Read [experiment-summaries.md](references/experiment-summaries.md) for what summaries in this repository need.
3. Draft or revise around the reader's question, keeping the sections in [the summary template](../../../docs/experiments/TEMPLATE.md). A wording change must not change a result, a threshold or a decision. If one has to change, say so separately.
4. Finish with the cold read in `experiment-summaries.md`.

The privacy rules in [AGENTS.md](../../../AGENTS.md) apply to every word: no participant names, transcript excerpts or private paths.

## Delivery

For an edit, say what changed and what you checked against which source. For a review, quote each passage, say what it stops the reader from understanding, and propose a replacement. Don't invent a problem to fill a review. These rules don't guarantee good writing, so say what a review couldn't check.
