# 2026-11-02: the saved-audio pipeline on the 17-recording synthetic collection

**Status: complete.** Turbo was the fastest recognizer on every spoken recording, but it did not always make the fewest errors. Word-level speaker attachment recovered the most turns, and splitting at long digital pauses helped full Whisper. Who merged speakers on all three clean four-person calls, yet beat Sortformer on the four-person overlap mix. Better transcriptions alone did not ensure better notes.

[Per-call measurements and input hashes](2026-11-02-expanded-pipeline-results.json) · [Fact and action verdicts bound to output hashes](2026-11-02-expanded-pipeline-judgments.json) · [Pipeline commands](../../experiments/pipelines/whisper-sortformer/README.md).

**Where this ran.** The collection is the one merged in #32 (`4c8c2f0`). The runs used development commits based on it, before the pipeline options they tested merged: `--language` (#33), `--asr turbo-q4` (#34), `--keep-asr-segments` (#35), and digital silence handling with `--split-digital-pauses` (#36). The development commits are not on `main`. Replaying the silence, split and segmented-line commands on the pipeline code in `main` gave the results described under [Pipeline options checked against saved outputs](#pipeline-options-checked-against-saved-outputs).

## Question and decision

Two experiments that are **not on `main`** made claims from smaller samples: a [seven-recording trial](https://github.com/pomodorozhong/meeting-recap/blob/c714e05/docs/experiments/2026-11-01-synthetic-collection.md) and a separate [action-evidence experiment](https://github.com/pomodorozhong/meeting-recap/blob/c714e05/docs/experiments/2026-11-01-action-evidence.md), both in draft PR #31. This experiment tests whether the trial's claims hold on a larger collection. Is Turbo always as accurate as full Whisper, and faster? Does Breeze win on sparse speech? Is Who faster but riskier with four voices? Does word attachment preserve more turns? Do clean transcripts rescue recap facts? The action-evidence claims are kept apart, because that experiment's prompts and reference labels are specific to it.

## Input and assumptions

Use all 17 hash-verified mono fixtures in the collection at `4c8c2f0`. Fourteen independent scripts (eight Mandarin including English terms, six English; one to four speakers). Report the two remixes and digital silence separately. The seven-recording trial used some of the same scripts, but synthesis and voices have changed since; only matching audio hashes are exact replications. One M2 Pro / 16 GB; serial local inference; generated text, timestamps and identities are known intended references, not listener judgments.

## Registered plan

The criteria below were fixed before the runs they govern, in the order shown. Their wording was edited later so that they read against `main`; no threshold, anchor or rule changed.

- Verify the fixtures with the synthetic project's collection.py --check. Keep results outside Git under benchmark ID expanded-pipeline-20261102. Preserve any failed cells. No listening session or clip selection; for turn order use review.py known at 4c8c2f0 (30 s windows), ref-CASE / eval-CASE.
- For each case, convert with the pipeline ffmpeg settings. Run the pinned MLX runners (word timestamps on, previous-text conditioning off, stock decoding) with full Whisper 49e6aa28, Turbo Q4 660c343b and Breeze 172151e3. Force the script's declared language; zh for controls. Also decode the six English inputs with full Whisper forced to Mandarin, the pipeline's default language. Report English WER and Mandarin CER separately with score_transcripts.py; track latency, footprint, and text on silence. Expect declaring English to improve WER. Keep Mandarin as the default; expose language explicitly if it wins.
- Run pinned Sortformer and Who on the same converted audio, score one-to-one speaker-time error with overlap and no collar. Compare all three attachment methods through the known-turn evaluator. Check overlap, attenuated audio, label counts, and four-voice subset separately. Check the trial's alternative-diarizer ranking on the clean four-voice onboarding and English committee calls using available pinned Community-1 and LS-EEND runners.
- Apply the trial's five-second exact-zero splitter (250 ms context), with language-matched decoding on all qualifying calls. For unchanged audio reuse the unsplit result. Keep it experimental unless neither language regresses. Distinguish internal pause errors from pure silence.
- Run Qwen3.5 9B at 8b2b98c0 via the pipeline, and again from the exact turns, on onboarding and English audit. Compare these nine preregistered semantic checks: onboarding turns 9, 10, 12, 14–16 (account test owner/time; documentation owner/time; test access restored; production access still separate/unapproved); English audit turns 2, 3, 7, 8/11, 10 (corrected adapter total; usable cable count; scale fault unresolved; corrected booking; delivery expected, not received). Score full / partial / absent or wrong; use anonymous labels mapped to reference by overlap. Also audit reopened questions and unsupported details. This is targeted unblinded review of synthetic content; no claims about all action precision or recall.
- Repeat full, Turbo and Breeze on one short clean case and silence to check text repeatability. Measure wall time and process footprint; no caching a model across timed invocations. No tuning on the scored scripts. Keep a candidate only as an option when results vary by call. Do not extrapolate to real rooms, longer meetings, or user-confirmed speaker identity.

### Speaker-count clarification and action check

Before any diarization or recap inference: the English committee script has **three** voices. Keep it, supply its actual count in the oracle-count condition, and add the four-voice English tabletop so a four-voice English test is present. This change follows fixture metadata, not predictions.

To test the action-evidence conclusions directly, use two further Mandarin scripts with explicit assignments. Freeze four anchors: scheduling turns 8/10 (B, update invitation and materials by 17:00) and 11 (A, test demonstration account by Thursday noon); localization turns 5 (B, revise on-screen text by Wednesday 15:00) and 6 (C, check operating instructions by Thursday noon). A strict anchor requires the right deliverable, owner, deadline and cited input lines that actually support all three; no credit for merely valid timestamp syntax. Score only these four anchors; unrelated valid tasks are not false positives. Use identical Sortformer segments for full/Turbo. Compare ordinary and focused extraction on exact and Turbo inputs, focused on full Whisper, then that experiment's citation verifier on Turbo-focused candidates. Also run its time-overlap speaker repair on those same Turbo lines. Use the frozen prompts, parser and label diagnostic at c714e053. Keep output/mapping, wall time and factual judgments external. That experiment's no-action precision claim, long-context proposals, and real-call findings cannot be established from these positive short scripts.

### Entirely silent input

Without a silence check, full Whisper emitted the same 20 alphanumeric characters twice on 12 seconds of digital zero; Turbo emitted 35 twice and Breeze emitted none twice. So add a conservative whole-input check before Whisper (merged in #36). Only a nonempty converted WAV whose samples are *all exactly zero* may skip ASR and produce an empty transcript and a no-speech recap without the LLM. Keep ordinary nonzero speech and internal pauses on the normal path. Verify the normal saved-audio command on the silence control and the two planned spoken recap calls. Include a quiet nonzero sample in the regression check. No assumption about room noise or audible silence is needed.

### Turbo + Who pipeline comparison

Before reading any recap from this experiment, also run the Turbo Q4 / Who combination end to end on the same onboarding and English audit recordings. Use identical spoken-language settings, the same Qwen prompt, the same nine checks, and the default full Whisper / Sortformer as the comparator. These two inputs stress different failure modes (four-speaker ownership versus single-speaker corrections). Full Whisper stays the default. This checks the trial's finding that faster component times and readable Markdown need not preserve owners, dates, or corrected decisions.

### ASR segment boundaries in recap input

The Turbo + Who English audit emitted 37 invalid citation timestamps and left 21 items without citations; the rendered mono transcript provided only two long lines. Test a formatting change on cached inputs: start a new timestamped transcript line at every Whisper segment boundary, still attaching each word to its diarization by overlap (now `--keep-asr-segments`, merged in #35). Keep the transcript and recap input lines identical, model, prompt, speaker names and segments fixed. Keep the merged-line outputs for comparison. Run the Turbo + Who audit (development) and onboarding (transfer) against those outputs. Add an English training comparison whose recaps had not yet been generated, using the same saved Turbo and Who predictions for both formats. Freeze three training anchors: final count of 18 verified (turns 7/8/18); A's checklist revision by Wednesday noon (21); B responsible for the practice check, due Thursday 10:00 (22).

For each format count lines, dropped citations and items without citations. Regrade the same facts; additionally count fully correct facts for which the cited lines, together, actually state the expected information (timestamps must refer to displayed lines, and owner checks use the same independently fitted label mapping). More valid timestamps alone is not a pass. Keep the change as an option only if the audit has fewer uncited items and at least one more fully supported anchor, with no loss of full factual anchors on any of the three cases. Otherwise keep it as a failed or mixed experiment. This is exploratory and the audit triggered it.

### Full-Whisper pause option

Full Whisper improved or tied on each of the four eligible non-silent cases, with no regression in either language aggregate. So offer the measured rule as an explicit option for this model only (now `--split-digital-pauses`, merged in #36), leaving normal nonzero decoding unchanged by default. Before acceptance, run the pipeline command on onboarding with `--split-digital-pauses --diarizer who --no-summary` and require the same normalized error count as the benchmark split, source-relative timestamps (including speech after the long gap), and a successful rendered transcript. Reusing a loaded model within this command is allowed; its wall time is not compared as though it were the benchmark's separate process per chunk. Verify that near-silent nonzero audio is not cut. This is not a room-noise or general VAD change.

## Restart

Use the locked synthetic and pipeline projects, pipeline setup and Swift binaries in their READMEs; use the MLX run.py CLI with repo, language and pinned revision. Use the collection's language-aware transcript scorer. Store raw calls, predictions and individual judgments outside Git. Public results contain counts and digests only.

Some definitions are not on `main`. score_case.py, turn_order.py and silence_split.py at c714e05 define the metrics carried over from the two #31 experiments, and expanded_actions.py reads its frozen action prompts from that commit, so it must be available locally (draft #31's branch holds it; fetch it if working from a shallow clone).

From the repository root, set `FIXTURES` to the verified collection and `RESULTS` to a **new absolute path** in the external benchmark directory. Prepare the pinned Whisper, Breeze, Turbo, Qwen, Sortformer and Who caches before timing. Community-1 and the four LS-EEND weight sets must match the tree hashes recorded with the seven-recording trial at c714e05.

```bash
S=experiments/synthetic-call
P=experiments/pipelines/whisper-sortformer
uv sync --locked --project "$S"
uv sync --locked --project "$P"
uv sync --locked --project experiments/mlx
swift build -c release --package-path "$P" --product fluidaudiocli
swift build -c release --package-path "$P" --product who-diarize
swift build -c release --package-path experiments/diarization --product diarexp
"$S/expanded_decode.sh" "$FIXTURES" "$RESULTS"
for phase in recaps diarize split turns; do
  "$S/.venv/bin/python" "$S/expanded_followup.py" "$FIXTURES" "$RESULTS" "$phase" || exit 1
done
"$S/.venv/bin/python" "$S/expanded_actions.py" "$FIXTURES" "$RESULTS"
"$S/.venv/bin/python" "$S/expanded_scores.py" "$FIXTURES" "$RESULTS" > "$RESULTS/scores.json"
```

For the line-format comparison, use `$P/.venv/bin/python "$P/compare_lines.py" ASR DIARIZATION CONVERTED_WAV NEW_OUTPUT`. On the two saved Turbo + Who pipeline runs use their `asr.json`, `diarization.json`, `audio.wav`, and `--speakers FAST/speakers.json --keep-segments`, where `FAST` is the run's folder; compare to its saved recap. For training use the case's `turbo.json`, `who.json` and `audio.wav` twice, first with default lines and then with `--keep-segments --speakers FIRST/speakers.json`.

The expanded_scores.py command is a model-free recalculation of the transcript, timing, speaker and pause measurements from saved outputs. Repeat semantic grading on fresh outputs, including their cited source lines; changed text cannot inherit an earlier judgment.

## Runtime and memory

One inference process ran at a time on the M2 Pro / 16 GB. Timings include process startup, model load and device teardown; the desktop was in normal use. A two-job Swift compilation overlapped part of the early English audit and silence timing. Toolchain caches were warm. These are individual observations on this machine, not latency guarantees.

| ASR, script-matched language | Median wall time, 17 fixtures | Total stage time | Peak process footprint | Fastest on |
| --- | ---: | ---: | ---: | --- |
| Full Whisper | 15.84 s | 344.99 s | 9.00 GB | 0 |
| Turbo Q4 | 7.86 s | 181.81 s | 4.14 GB | All 16 speech recordings |
| Breeze | 30.59 s | 640.58 s | 12.92 GB | Digital silence |

## Results and limits

### Recognition

The 17 audio files span 33.76 minutes. Two WAVs are byte-identical to the seven-recording trial's (stocktake and digital silence); five of its conditions now have different waveforms. Fourteen independent source calls contribute to language scores. The stressed handoff and logistics mixes repeat source text and are excluded. Each rate is total edits divided by total language-specific reference units.

| Word-timestamp recognizer | English WER (6 calls; 3,028 words) | Mandarin CER (8 calls; 3,095 characters) |
| --- | ---: | ---: |
| Full Whisper, Mandarin forced everywhere | 84.41% (2,556) | 9.98% (309) |
| Full Whisper, declared language | 2.18% (66) | 9.98% (309) |
| Turbo Q4, declared language | **1.98% (60)** | **7.59% (235)** |
| Breeze, declared language | 7.43% (225) | 12.08% (374) |
| [Full Whisper component baseline](../../experiments/synthetic-call/reference/transcript-baseline.json), no word timestamps | 1.88% (57) | 9.27% (287) |

Declaring English improved every English call. The trial's “Turbo never loses” result **does not hold**: full Whisper made fewer edits on four Mandarin scripts (planning, scheduling, design, localization) and two English scripts (design, tabletop). Turbo's 74-edit aggregate Mandarin advantage includes 66 edits from onboarding. No word-timestamp configuration beats the component baseline in both language groups. That baseline also uses temperature zero; the pipeline-style arms use the decoder defaults. The comparison does not isolate timestamping as the cause.

On the stocktake WAV shared with the trial, its 48/48/17 errors for full/Turbo/Breeze repeated. On the resynthesized logistics pair all three worsened with overlap (28→35, 20→34, 17→31 edits). On the attenuated handoff the changes were 32→13, 13→16, 11→11: the trial's finding that Breeze improved on that specific degradation did not repeat. On the shared silence WAV full/Turbo/Breeze again emitted 20/35/0 normalized characters. Both raw-versus-repeat checks matched each model's normalized text on handoff and silence. Generated scripts are intended speech; TTS pronunciation can contribute to text errors.

### Speaker identity and timing

Speaker-time error is (missed + false-alarm + confused speaker-seconds) / reference speaker-seconds, pooled only over independent scripts in each row. One-to-one optimal mapping per file, overlap included, zero collar. Scripted turn intervals include pauses within TTS utterances, so time error also penalizes some valid silence detection. Speaker count and precision of the delivered transcript are separate measures.

| Script speakers | Independent calls | Sortformer | Who int8 |
| ---: | ---: | ---: | ---: |
| 1 | 2 | 12.06% | 7.89% |
| 2 | 4 | 5.66% | 2.74% |
| 3 | 5 | 10.51% | 3.34% |
| 4 | 3 | **9.94%** | 26.86% |

Who produced three labels for four speakers on all three clean four-voice calls. The known one-voice stocktake split into two labels with Who, as it did in the trial (28.7% versus Sortformer 11.2%); the three-person planning call split into four labels with both. Sortformer also split voices on scheduling and design. Who's better aggregate on one through three voices does not predict every recording.

The matched four-person overlap mix **reverses the clean result**: both found four labels, and Who had 13.6% error versus Sortformer 20.4%. The trial's overlap mix favored Sortformer (12.1% versus 25.2%). On the attenuated handoff, Who kept its advantage (4.9% versus 15.0%). Neither emitted speech on digital silence; a percentage error there is undefined.

Across all 17 standalone diarizer runs, Who took 9.34 s in total (median 0.57 s; peak 0.275 GB) versus Sortformer 888.55 s (median 33.03 s; peak 0.847 GB), about 95× less total time. The separate Turbo + Who onboarding pipeline run had a 20.77 s Who load and 0.37 s of inference: these timing summaries do not guarantee a subsecond cold start.

In the separate three-case alternative-model sweep, Sortformer beat all four LS-EEND variants and both Community-1 settings on each call. Automatic / oracle-count Community-1 errors were 62.7% / 51.2% on onboarding, 54.6% / 26.1% on tabletop, and 70.9% / 70.9% on committee. On committee both settings returned just one of three voices. LS-EEND AMI beat Who on onboarding (18.2% versus 41.8%), but trailed Sortformer (13.8%). These results concern the pinned FluidAudio ports, not the original gated pyannote implementation.

### Silence splitting and attachment

| Speech with a qualifying pause | Full Whisper edits, whole → split | Turbo edits | Breeze edits |
| --- | ---: | ---: | ---: |
| Stocktake (Mandarin; same audio as the trial) | 48 → 18 | 48 → 21 | 17 → 25 |
| Onboarding (Mandarin) | 91 → 11 | 25 → 20 | 18 → 21 |
| Audit (English) | 16 → 16 | 12 → 12 | 16 → 52 |
| Training (English) | 14 → 11 | 11 → 11 | 19 → 28 |

The other 12 speech WAVs pass through without a change; digital silence yields empty text. Across the 14 independent scripts, split full Whisper reaches 6.43% Mandarin CER and 2.08% English WER. Turbo reaches 6.56% and 1.98%; Breeze worsens in both languages (12.44% and 8.92%). This is a five-second digital-zero rule, not evidence about splitting acoustic pauses. One whole-file Breeze gap diagnostic lacks word timestamps and is unavailable, not zero. The text remains scoreable.

The skill evaluated 16 non-silent recorded mixes, no excluded clips. Across the 14 independent scripts, full Whisper + Sortformer with word / segment / line-end attachment recovered **258 / 254 / 252 of 270 turns** and **47 / 43 / 40 of 61 whole clips**. With Who the corresponding figures were 250 / 244 / 243 turns and 46 / 41 / 40 clips. For Breeze, six word-attachment arms on three English recordings were refused; comparing like with like on 11 scripts, word / segment / line-end recovered 192 / 191 / 189 of 204 turns with Sortformer and 185 / 185 / 182 with Who. Known-turn scores use fitted mappings per run and measure ordered turns in reference windows, not whole-call DER.

On the planning call, full Whisper + Sortformer labeled 1,355/1,385 characters correctly at ASR word times (97.8%), but only 1,259/1,314 aligned characters in the delivered transcript (95.8%). With Who the figures were 1,360/1,385 (98.2%) and 1,266/1,314 (96.3%). The trial's relative ordering, and its drop after attachment, appear here too. Unlike the one-to-one time metric, this word metric fits a many-to-one label map and can hide a split speaker.

### End-to-end recaps

| Input | Full Whisper + Sortformer | Turbo + Who | Exact turns + identical recap model |
| --- | ---: | ---: | ---: |
| Onboarding (4 checks) | 2 full, 1 partial; 135.66 s | 2 full, 1 partial; 68.97 s | 3 full; 29.57 s |
| English audit (5 checks) | 5 full; 159.30 s | 4 full, 1 partial; 80.01 s | 3 full, 2 partial; 53.77 s |
| Full facts across the two calls | **7/9** | **6/9** | **6/9** |

Wall times in the first two columns start from audio; the exact column times only summarization from known turns. The nine anchors are targeted factual checks in any section, not a precision estimate. A correct value with a contradictory correction or a reopened final status earns partial credit. Anonymous labels are mapped by maximum shared speaker time. This is one unblinded grading of intended synthetic speech.

Default onboarding retained both assignments; Turbo + Who merged speakers and lost the test owner, while recovering the separate production-access decision. All three omitted the successful test retry. On audit, the default recovered the facts but reopened settled counts as proposals. The exact-input recap misstated the superseded booking day and reopened receipt of the delivery. The Turbo + Who recap stated delivery had not arrived and also asked whether it had. It had 37 invalid citations removed and 21 items left uncited; all the other recaps in this table had zero of either. One default English recap was in English despite a prompt requesting Traditional Chinese. These findings qualify both of the trial's claims: cleaner input can help, but is no guarantee; similar time or aggregate check counts do not establish equivalent factual notes.

On the silence control, the pipeline returned zero transcript turns and zero recap items in 6.69 s, with ASR and summary marked as skipped. It still checked and ran the selected diarizer. This is an exact-digital-zero check, not a voice activity detector.

### Action recovery and evidence

| Frozen condition on scheduling and localization | Strict target hits / 4 | All rows emitted | Total model-stage wall time |
| --- | ---: | ---: | ---: |
| Exact / ordinary recap | 4 | 6 | 79.6 s |
| Exact / focused pass | 4 | 7 | 35.6 s |
| Turbo / ordinary recap | 2 | 7 | 82.0 s |
| Turbo / focused pass | 2 | 8 | 41.2 s |
| Turbo / corrected line labels / focused | 3 | 8 | 41.3 s |
| Full Whisper / focused | 2 | 8 | 39.2 s |
| Turbo / verifier after focused pass | 0 | 0 | 22.1 s extra |

These are **four prespecified anchors**, not all outstanding tasks; dividing by emitted rows would not measure precision. Exact input helped here. The action-evidence experiment's full-versus-Turbo strict-action advantage (7/14 versus 4/14 on different meetings) and its focused-versus-ordinary advantage do not repeat: both audio extractors retained the two localization anchors. On scheduling the focused Turbo recap predicted the right account test, but its only citation started midway through the word distinguishing the intended account; the strict verdict is a miss. Accepting a plausible reconstruction would credit an additional scheduling anchor to Turbo ordinary/focused and the repaired pass, not to the full-Whisper row that changed the task itself. Perfect time-overlap labels changed the wording and recovered one other scheduling commitment; this uses the reference and is a diagnosis, not a deployable repair. That experiment's verifier result **did** repeat: the verifier discarded all eight candidates, including two strict hits. Leave it out.

### Pipeline options checked against saved outputs

The normal full-Whisper command with `--split-digital-pauses --diarizer who --no-summary` matched the onboarding split result: **11 edits instead of 91**. The two source spans and all 274 recognized words and their start/end times matched the experiment, including 105 words after the pause. It rendered 17 transcript lines in 21.45 s end to end.

With identical Turbo words, Who labels and recap prompt, keeping Whisper segment boundaries gave the recap more precise lines to cite:

| Call | Transcript lines, merged → segmented | Uncited items | Fully correct facts | Fully correct with supporting citations |
| --- | ---: | ---: | ---: | ---: |
| English audit (5 checks) | 2 → 21 | 21 → 0 | 4 → 4 | 2 → 4 |
| Onboarding (4 checks) | 19 → 46 | 0 → 0 | 2 → 3 | 2 → 3 |
| English training (3 checks) | 22 → 48 | 0 → 0 | 2 → 2 | 2 → 2 |

The audit went from 37 invalid citations removed to zero. Onboarding recovered the successful retry with supporting evidence; the merged speaker still caused a wrong owner. Neither training recap stated that 18 was the **verified final** count; both kept the assignments. Some segmented lines start in the same displayed second, so a timestamp may still be ambiguous. The option passed the registered gate, including the previously unseen training recap. The normal `run --asr turbo-q4 --diarizer who --language en --keep-asr-segments --no-summary` command on the audit matched the graded segmented transcript byte for byte. Only the audit triggered the experiment. These are paired examples, not an estimate of general recap accuracy.

## Decision and open questions

Keep full Whisper, Sortformer and word-level attachment as the conservative default. Specify the spoken language; offer Turbo for turnaround and Who when speaker identity can be checked. Use the optional exact-zero splitter on digitally muted or edited inputs, and the optional shorter lines when the recap needs finer citations. Skip ASR and recap generation on exact whole-file silence. Do not adopt the verifier or a reference-assisted speaker repair. Keep full and fast recaps reviewable: even an accurate transcript and valid citation can accompany a wrong statement.

The two WAVs shared with the trial check repeatability; changed voices and remixes check whether its findings hold on other audio. They cannot separate voice, overlap and script effects across unrelated calls. The action-evidence experiment's 24-item prompt comparison was not repeated on its original task here; the focused action results above cover only four specified positive commitments. No-action precision, long meetings, real-room noise, and accuracy against a listener-confirmed reference remain open. Next, check owners, decisions and citation support on the already prepared private listening reviews before changing the default.
