# Ten synthetic calls for evidence-backed actions

**Status** Planned, 2026-11-01.

## Question

Can a focused extractor improve the number of real outstanding commitments returned with the correct owner, deadline and supporting evidence? Which losses persist with a perfect transcript? This builds on the [seven-recording benchmark](2026-11-01-synthetic-collection.md), where four of nine recap checks passed on pipeline transcripts and nine on scripts.

## Input and answer keys

Ten independent, fictional Mandarin calls with two to four preset voices cover owner reassignment, deadline correction, separate commitments with similar objects, a completed task, cancellation, conditional proposals, unstated owners or dates, multiple evidence turns and a meeting with no outstanding actions. Freeze the scripts and keys before synthesis. Each gold item gives a task, owner (or null), deadline (or null) and one-based supporting script turns. Generate with the existing Qwen3-TTS pin and seed 7. Full recordings are scored without clip selection or listening sessions.

## Registered comparisons

Use one paired two-by-two experiment across all ten calls. ID each run by call, transcript source (exact script or audio) and prompt (ordinary recap or focused actions). Use one audio transcript per call from Turbo Q4 and Sortformer, pinned in the saved-audio pipeline. For both prompts use the same Qwen3.5-9B 4-bit revision, greedy decoding, thinking disabled and the same timestamped lines per source. The focused prompt requests only final outstanding tasks, applies the latest accepted owner and date, excludes conditional, withdrawn and completed work, permits an empty list and asks for every line needed for support. Neither prompt sees the key. Expect fewer false positives and faster generation with focused extraction.

Run locally in serial on the M2 Pro / 16 GB. Record wall time and peak process footprint separately. Compare strict micro precision, recall and F1 plus per-call misses and false positives. One prediction can recover one gold action, once. For a strict hit, its task, mapped owner, deadline and cited text must all support the final commitment. An absent owner/date must remain unknown. Valid timestamps alone are insufficient. A human-language paraphrase is allowed. Inspect every output autonomously against the frozen key and the actual cited transcript lines, retaining row-level verdicts and digests for replay. Map anonymous output speakers to script identities from their timed overlap, independently of the recap. Score an empty-gold call by its false positives. Never infer a user-confirmed reference.

## Reproduce

Build the action scripts using the synthetic-call generator, run the two-by-two matrix and replay its verdicts. Commands and measured outcomes follow after execution.

### Registered speaker-label diagnostic

The main exact/audio contrast changes both words and speakers. Add a focused-only replay for all ten calls that keeps every recovered line's wording, timestamp and boundary fixed. Replace its displayed speaker with the script speaker with the greatest time overlap with that ASR turn (unknown for no overlap). Run the identical focused prompt, then score identically with script identities. This tests line-level attribution without using the action key. A mixed-speaker line or incorrect ASR timing can still defeat the repair. Keep this diagnostic separate from the four primary cells.
