# Experiment summaries

These rules cover what general writing advice misses in a summary of an experiment. The reader knows the project's goal but hasn't seen this experiment, its history, or the conversation behind it.

## Say what the numbers count

Define a metric the first time it appears, including its unit and which direction is better. Label every value in a series, so the reader never has to work out which number belongs to which model.

- **Unclear:** "the changes were 32→13, 13→16, 11→11."
- **Clear:** "Compared with the clean recording, the noisy version went from 32 to 13 edits for full Whisper, 13 to 16 for Turbo, and 11 to 11 for Breeze."

An edit is one inserted, deleted or substituted unit. A summary that uses "edits" says so, and says that the unit is a character in Mandarin and a word in English.

## Replace private shorthand

Words that make sense during an experiment mean little afterward. Replace them with plain words, or explain them where they first appear in that summary. Each summary may be the only one a reader opens.

| Instead of | Write |
| --- | --- |
| arm, condition | the setting or model itself: "Turbo with the declared language" |
| anchor | "a fact the recap has to state" |
| gate | "the pass rule set before the test" |
| the trial, earlier, old, new | the named experiment: "the seven-recording trial in draft PR #31" |
| fast, ordinary, shipping | the actual option: "Turbo + Who", "full Whisper forced to Mandarin" |
| diagnostic, control | what it checks: "a recording of digital silence, to see whether models invent text" |

Keep a technical name when it's the right one, such as WER or a command-line flag, and explain it once.

## Describe only procedures that exist

Any advice to check, review or confirm something must say who does it, with what, and what they can do about a problem. If no tool exists, say so. Don't imply a safety net that isn't there.

- **Unclear:** "Offer Who when speaker identity can be checked."
- **Clear:** "Who can merge people under one label, and editing `speakers.json` can't split a label. If a run shows fewer labels than the people who spoke, rerun with Sortformer."

If you infer a procedure from the results and didn't test it, say that.

## Keep each summary to one question

A summary answers one question and supports one decision, even when several summaries share a run. If a section needs a different decision, it belongs in a different summary. When a run has results a summary leaves out, say that they exist and where they are. Don't leave them out silently.

## Say how each test came about

Separate what was planned before the runs from what a result prompted. For a test a result prompted, say which result, and what that means for trusting it. A call that prompted a fix is likely to flatter that fix.

Say "planned" and "added after seeing X". Don't use "preregistered" or "exploratory" without saying what happened.

Git shows when text was committed, not when a run happened. If the commits can't establish whether a test was planned before its run, say that, and don't claim it was.

## Check sources before rewording

Rewording can change a claim without anyone noticing. Before rewriting a sentence, check each number against the results file, and check each attribution against the document it credits. Make sure a sentence crediting "the trial" isn't describing a different experiment.

Don't add a cause, a comparison or a caution the evidence doesn't support. When a rewrite adds a real caution, say so in the PR so that a reviewer can judge it.

## Explain what a result can't show

State the limit and its consequence for the reader, with an example where one exists.

- **Unclear:** "They can't separate voice, overlap and script effects across unrelated calls."
- **Clear:** "Unrelated calls differ in voices, overlap and script all at once, so when results differ, we can't tell which of those caused it. For example, Sortformer won one four-person overlap mix and Who won another, and we don't know why."

Say how much evidence a conclusion rests on, such as "12 facts from three calls, graded once", next to the conclusion. Say who graded or judged something only if you know.

## Cold read

Before committing, read the summary in order as someone arriving from the experiments index, then check that:

1. The Outcome alone says what was found and what was decided, in words the reader already knows.
2. Every number has a label, a unit and a direction.
3. Every term is either familiar or explained where it first appears.
4. The Decision answers everything "Decision it informs" names, follows from results shown in this summary, and gives its real reasons. If the evidence doesn't favor the choice, say that the choice is cautious, not that it won.
5. Anyone following a piece of advice would know what to do next.
6. Anything not on `main` is named as such.
