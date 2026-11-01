# Ten synthetic calls for evidence-backed actions

**Status** Complete, 2026-11-01.

Across the ten new calls, full Whisper with focused extraction returned **7 of 14** fully supported actions, versus **4 of 14** for Turbo with the same extractor. The larger model recovered three additional commitments across three different calls. It still missed half. [Per-call measurements](2026-11-01-action-evidence-results.json), [row-level semantic verdicts](../../experiments/synthetic-call/reference/action-verdicts.json) and the [original scoring inputs](../../experiments/synthetic-call/reference/action-replay.json) are saved with this report.

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

### Registered ASR comparison

The primary audio-focused extractor recovered four of fourteen strict hits. Test whether substituting full Whisper Large v3 improves the same downstream measure. On all ten recordings run the ordinary saved-audio pipeline with `--asr large-v3 --diarizer sortformer --no-summary`, then the frozen focused prompt. Use the same overlap mapping, evaluator and gold keys. Compare each rerun's diarization digest with its Turbo counterpart and report any differences, since those pairs would change two components. Report action gains or losses, transcription wall time and footprint. This is an exploratory comparison prompted by the completed primary matrix.

## Reproduce and score

The [run instructions](../../experiments/synthetic-call/README.md#action-evidence-benchmark) generate the ten WAVs locally, run the primary matrix and speaker-label diagnostic, then replay the semantic verdicts. The [scripts and keys](../../experiments/synthetic-call/action-scripts/) were committed at `e3ed1ea` before generating audio. The frozen extraction prompt and driver are at `c364744`, the label diagnostic at `2df0eb4`. The 55 turns produced 224.94 seconds of audio. The synthesizer reported 182.2 seconds across the ten model loads and synthesis loops. All WAVs passed digest, reference alignment, duration and signal-level checks.

The [model-free replay command](../../experiments/synthetic-call/README.md#replay-the-published-scores-without-models) checks the original 200 scoring artifacts against all 70 published cells and aggregate fields. The 2026-11-02 reproducibility check reproduced the saved report exactly, including recorded timings, without inference. A fresh model run still needs fresh semantic judgments if its output bindings differ. The full-run recipe now caches both ASRs with `setup --asr all`, preflights the complete matrix, and restores Sortformer from an immutable revision.

The ordinary condition uses the normal single-chunk recap prompt and scores its action-items section. The focused condition emits only action items. Both use Qwen3.5-9B-4bit at `8b2b98c00a6b4d291155e4890773ca8f769aee53`. Input audio is transcribed once per call using Turbo Q4 at `660c343bbf4e52ac257f0b7d952e5388e6f93bef` and Sortformer at the saved pipeline's pinned weight digest.

For semantic grading the agent saw the frozen task key, predicted action, mapped owner and the actual text at its cited timestamps. The packet hides prompt and condition names and presents content-hashed rows. Identical rows are judged once. Wording and transcription artifacts can still reveal the source. The grader accepts paraphrases, but a garbled or changed deliverable, recipient or material scope loses task credit. An invented date, missing part of a deadline, wrong owner, missing citation or a real citation that fails to support the final action loses strict credit. A row in another recap section does not count. Counts are paired per meeting, with at most one strict hit per gold action. This is agent judgment on intended synthetic speech.

**Execution note.** The no-action exact focused run returned a literal empty JSON array. The original parser refused it before the next stage. Preserve the first attempt and record this unambiguous abstention as a schema deviation. Accept only an empty array as this special case, keep the prompts fixed, and retry the interrupted call.

## Runtime and strict scores

The matrix contains 70 case/condition results across ten recordings. Four verification conditions had no candidates and therefore invoked no summary model. The interrupted first attempt on the negative control is retained locally and excluded from timing and scores. Runs used the M2 Pro with 16 GB; model inference processes ran serially. Summary timings include process startup and model load. The verification row gives **incremental** latency on top of focused extraction, including zero model time for the four empty inputs.

| Condition | Emitted | Task hits | All fields correct | Evidence-backed hits / 14 | Precision | Recall | F1 | Median extraction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Exact / ordinary | 15 | 13 | 12 | 11 | 73% | 79% | 0.759 | 21.9 s |
| Exact / focused | 15 | 13 | 11 | 10 | 67% | 71% | 0.690 | 11.0 s |
| Turbo / ordinary | 13 | 6 | 4 | 2 | 15% | 14% | 0.148 | 23.2 s |
| Turbo / focused | 9 | 4 | 4 | 4 | 44% | 29% | 0.348 | 9.6 s |
| Turbo / repaired labels / focused | 8 | 4 | 4 | 4 | 50% | 29% | 0.364 | 10.5 s |
| Turbo / focused + verification | 0 | 0 | 0 | 0 | — | 0% | 0.000 | 7.8 s |
| Full Whisper / focused | 13 | 7 | 7 | 7 | 54% | 50% | 0.519 | 11.3 s |

Every hit counts a unique action. “Task hits” require the intended deliverable including material scope or recipient. “All fields correct” additionally requires owner and deadline. Strict hits additionally require complete, semantically supporting citations. Precision divides strict hits by emitted rows; recall divides them by the 14 gold actions. The same calls are reused across conditions.

### Per-call strict hits / emitted rows

| Call | Gold | Exact, ordinary | Exact, focused | Turbo, ordinary | Turbo, focused | Repaired labels | Verified | Full Whisper |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| archive | 2 | 1/1 | 1/2 | 0/1 | 0/2 | 0/1 | 0/0 | 0/1 |
| freezer | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/0 | 0/1 |
| inventory | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/0 | 0/0 |
| keys | 2 | 1/2 | 1/2 | 1/2 | 1/2 | 1/2 | 0/0 | 1/2 |
| menu | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/0 | 1/1 |
| museum | 0 | 0/1 | 0/0 | 0/1 | 0/0 | 0/0 | 0/0 | 0/0 |
| podcast | 2 | 2/2 | 2/2 | 0/1 | 0/0 | 0/0 | 0/0 | 1/2 |
| poster | 2 | 2/2 | 1/2 | 0/2 | 2/2 | 2/2 | 0/0 | 2/2 |
| rainplan | 1 | 1/2 | 1/2 | 0/1 | 0/0 | 0/0 | 0/0 | 1/2 |
| tickets | 2 | 1/2 | 1/2 | 0/2 | 0/0 | 0/0 | 0/0 | 1/2 |

The focused prompt's two extra strict hits over the ordinary prompt on Turbo audio were both on the poster handoff. The comparison does not establish a broad prompt advantage across scenarios. Full Whisper preserved all four Turbo-focused hits and gained one on each of the podcast, classroom reservation and ticket-dispatch calls. The new true positives came with one additional strict false positive in aggregate (six versus five).

## Findings

Every primary emitted item had a syntactically valid citation. The ordinary recap on audio nevertheless recovered only two strictly supported actions. It identified six of the fourteen tasks, got all fields right for four, and cited sufficient evidence for two. The focused pass identified four tasks, got all fields right for those four and cited sufficient evidence for all four. Its precision increased because it returned fewer unsupported claims. It also missed ten real actions. On exact transcripts the ordinary recap recovered eleven strict hits and the focused extractor ten. The observed benefit of focusing the prompt depended on the quality of its input.

The no-action control matters for interpreting precision. Given a completed upload, a withdrawn proposal and an unanswered question, the ordinary recap invented one pending action from each input source. The focused extractor abstained on both. On the multi-turn key handoff, answers could have the right fields yet cite the deadline without the recipient or cite the recipient without the owner's acceptance. On the podcast call, an output recovered the intended deliverable while its cited ASR text named a different object. Such rows fail the evidence requirement even when the intended task is easy to guess from the script.

### Speaker and citation diagnostics

Only three of the sixty rendered lines changed speaker in the time-overlap diagnostic. Those changes occurred in three different meetings. The focused run still recovered four supported actions and emitted eight rows, against nine before the repair. This cohort has short turns from distinct preset voices. A small label effect here provides little evidence about overlapping real meetings.

The citation verifier rejected **all nine candidates**, losing all four true positives along with the five false positives. Four calls had no focused candidates and skipped model loading. On the other six, the verifier ran and returned empty selections, including for an explicitly supported menu-publishing task. No citations were repaired. Precision is undefined when a filter returns nothing. Do not put this verifier in the default pipeline.

### ASR cost and decision

The ten diarization outputs were byte-identical across the two ASR pipelines. Full Whisper took 73.38 s for ASR over the ten files, versus 43.72 s for Turbo. Per-call median ASR wall time was 7.19 versus 4.21 s. Peak ASR process footprints were 5.57 versus 2.00 GB; the local Qwen extraction stages peaked at 6.61 GB. These are per-process decimal GB. The larger ASR and summarizer run one at a time.

Use full Whisper plus the focused prompt as the accuracy comparator for the next action benchmark. Keep Turbo as the faster comparator. The earlier seven-recording result favored Turbo on character error; that measure alone could not predict recovery of owners, deliverables and dates on these new scripts. Keep the verifier out of the normal pipeline. A useful next unattended check is an independent set of naturally paraphrased commitments with prerequisites and time qualifiers, graded before inspecting model output.

Fourteen intended commitments, synthetic voices, short scripted turns and one agent grader limit generalization. The reference describes intended words. A TTS pronunciation defect and an ASR substitution can have the same effect on the measured task. The verifier and full-ASR comparison were registered after earlier outputs were inspected, so treat their results as exploratory. No real meeting or user-confirmed listening answer contributed to these scores.
