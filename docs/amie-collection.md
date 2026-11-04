# Collecting Amie's own output

Amie is a competing pipeline: its transcript and summary are candidates to grade, not ground truth. Sixteen real recordings with Amie's output were collected into the private review dataset as `amie-001` to `amie-016` (2026-11-04). Nothing from them is in this repository. Each recording is `recordings/amie-NNN/` and Amie's output is its run `runs/amie-amie-NNN/` with the artifacts `summary` and `amie-transcript`; a private index of Amie's note titles is `raw/amie-index.json` in the dataset.

What the set holds: mostly Mandarin calls of 16 to 154 minutes, with 2 to 7 speaker labels in Amie's transcript. The labels are Amie's guesses, not counted speakers.

## What Amie's export looks like

- **Audio:** the original, mono AAC in m4a at 48 kHz. Amie's Download button opens it in the default browser's player, which cannot be driven by computer use. The note's public page has a hidden Download button that gives the same storage link.
- **Transcript:** "Copy transcript" gives plain text, one `Speaker N: text` line per turn. The copy has no timestamps or word times, though the app shows a start time per turn.
- **Summary:** "Copy summary" gives plain text. There is no export button. The Action Items and Private notes tabs were not collected.

## Pitfalls

- Reading the clipboard with `pbpaste` in a shell with no UTF-8 locale turns every Chinese character into `?`. Use `LC_ALL=en_US.UTF-8 pbpaste` and check the file is UTF-8.
- "Copy link" in Amie makes the note publicly viewable, and no way to turn that off was found. Collect the audio another way if the calls must stay private.
- The summary's template and whether the transcript was hand-corrected were not verified; the run notes say so.
