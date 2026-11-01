# Ten synthetic calls for evidence-backed actions

**Status** Runs in progress, 2026-11-01.

## Question

Can a focused extractor improve the number of real outstanding commitments returned with the correct owner, deadline and supporting evidence? Which losses persist with a perfect transcript? This builds on the [seven-recording benchmark](2026-11-01-synthetic-collection.md), where four of nine recap checks passed on pipeline transcripts and nine on scripts.

## Input and answer keys

Ten independent, fictional Mandarin calls with two to four preset voices cover owner reassignment, deadline correction, separate commitments with similar objects, a completed task, cancellation, conditional proposals, unstated owners or dates, multiple evidence turns and a meeting with no outstanding actions. Freeze the scripts and keys before synthesis. Each gold item gives a task, owner (or null), deadline (or null) and one-based supporting script turns. Generate with the existing Qwen3-TTS pin and seed 7. Full recordings are scored without clip selection or listening sessions.

## Registered comparisons

Use one paired two-by-two experiment across all ten calls. ID each run by call, transcript source (exact script or audio) and prompt (ordinary recap or focused actions). Use one audio transcript per call from Turbo Q4 and Sortformer, pinned in the saved-audio pipeline. For both prompts use the same Qwen3.5-9B 4-bit revision, greedy decoding, thinking disabled and the same timestamped lines per source. The focused prompt requests only final outstanding tasks, applies the latest accepted owner and date, excludes conditional, withdrawn and completed work, permits an empty list and asks for every line needed for support. Neither prompt sees the key. Expect fewer false positives and faster generation with focused extraction.

Run locally in serial on the M2 Pro / 16 GB. Record wall time and peak process footprint separately. Compare strict micro precision, recall and F1 plus per-call misses and false positives. One prediction can recover one gold action, once. For a strict hit, its task, mapped owner, deadline and cited text must all support the final commitment. An absent owner/date must remain unknown. Valid timestamps alone are insufficient. A human-language paraphrase is allowed. Inspect every output autonomously against the frozen key and the actual cited transcript lines, retaining row-level verdicts and digests for replay. Map anonymous output speakers to script identities from their timed overlap, independently of the recap. Score an empty-gold call by its false positives. Never infer a user-confirmed reference.

### Registered speaker-label diagnostic

The main exact/audio contrast changes both words and speakers. Add a focused-only replay for all ten calls that keeps every recovered line's wording, timestamp and boundary fixed. Replace its displayed speaker with the script speaker with the greatest time overlap with that ASR turn (unknown for no overlap). Run the identical focused prompt, then score identically with script identities. This tests line-level attribution without using the action key. A mixed-speaker line or incorrect ASR timing can still defeat the repair. Keep this diagnostic separate from the four primary cells.

### Registered citation verification experiment

On the first five completed calls, some correct fields lacked sufficient cited lines. Test an additional pass on the audio-focused output of all ten calls. Give the same local Qwen model the original recovered lines and numbered candidate rows. It may either reject a row or choose supporting line numbers for it. It cannot change the task, owner or deadline, add candidates or read the gold key. Convert its selected lines back to timestamps and judge against the identical rubric. With no candidates, return an empty list without inference. Compare supported hits, removed true and false positives, added citation support and incremental wall time against the single focused pass. This experiment was designed after inspecting the first five cases.

## Reproduce and score

The [run instructions](../../experiments/synthetic-call/README.md#action-evidence-benchmark) generate the ten WAVs locally, run the primary matrix and speaker-label diagnostic, then replay the semantic verdicts. The [scripts and keys](../../experiments/synthetic-call/action-scripts/) were committed at `e3ed1ea` before generating audio. The frozen extraction prompt and driver are at `c364744`, the label diagnostic at `2df0eb4`. The 55 turns produced 224.94 seconds of audio. The synthesizer reported 182.2 seconds across the ten model loads and synthesis loops. All WAVs passed digest, reference alignment, duration and signal-level checks.

The ordinary condition uses the normal single-chunk recap prompt and scores its action-items section. The focused condition emits only action items. Both use Qwen3.5-9B-4bit at `8b2b98c00a6b4d291155e4890773ca8f769aee53`. Input audio is transcribed once per call using Turbo Q4 at `660c343bbf4e52ac257f0b7d952e5388e6f93bef` and Sortformer at the saved pipeline's pinned weight digest.

For semantic grading the agent saw the frozen task key, predicted action, mapped owner and the actual text at its cited timestamps. The packet hides prompt and condition names and presents content-hashed rows. Identical rows are judged once. Wording and transcription artifacts can still reveal the source. The grader accepts paraphrases, but a garbled or changed deliverable, recipient or material scope loses task credit. An invented date, missing part of a deadline, wrong owner, missing citation or a real citation that fails to support the final action loses strict credit. A row in another recap section does not count. Counts are paired per meeting, with at most one strict hit per gold action. This is agent judgment on intended synthetic speech.
