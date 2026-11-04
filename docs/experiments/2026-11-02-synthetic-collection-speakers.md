# 2026-11-02: diarizers and label attachment on the 17-recording synthetic collection

**Status:** complete

**Outcome:** Who took about 95× less total time than Sortformer and had lower error on one to three voices, but merged speakers on all three clean four-person calls, and beat Sortformer on the four-person overlap mix. Word-level attachment recovered the most turns. Sortformer and word attachment stay the default. Who is offered when speed matters more than speaker accuracy, especially with one to three speakers.

## Reproduce

| Step | Command |
| --- | --- |
| Set up once (needs the network) | `experiments/synthetic-call/collection_setup.sh` |
| Run everything | `experiments/synthetic-call/collection_run.sh "$FIXTURES" "$RESULTS"` |
| Rerun this summary's steps | `experiments/synthetic-call/collection_run.sh "$FIXTURES" "$RESULTS" --step diarize`, then `--step turns` |
| Check saved results without models | `uv run --project experiments/synthetic-call experiments/synthetic-call/collection_scores.py "$FIXTURES" "$RESULTS" > scores.json` |

- **It needs:** `FIXTURES`, the verified collection built by [`collection.py`](../../experiments/synthetic-call/README.md#seventeen-recording-collection), and `RESULTS`, a new absolute path outside Git. `turns` also needs the full Whisper and Breeze outputs of the `decode` step.
- **It writes:** every model output under `RESULTS`, with the measurements in `RESULTS/scores.json`. This is one run shared by [several summaries](../../experiments/synthetic-call/README.md#compare-the-pipeline-on-this-collection), so the scorer needs every step's outputs. [The saved measurements](2026-11-02-synthetic-collection-results.json) are the committed copy.
- **Takes about:** 16 minutes for `diarize`, in the saved timings; `turns` wasn't timed. The whole run takes about 54 minutes, plus the untimed `turns` and `replays` steps.
- **By hand:** nothing for this summary.
- **Expect to differ:** timings on any rerun, and possibly model output on another machine. The scorer recalculates the measurements from saved outputs, so it should match the committed file byte for byte.

The setup script also restores the Community-1 and LS-EEND weights from the pins in [`alternative-diarizers.json`](../../experiments/synthetic-call/reference/alternative-diarizers.json).

## Question

Is Who faster but riskier with four voices? Do Community-1 or LS-EEND beat Sortformer? Does word attachment preserve more turns than segment or line-end attachment?

- **Decision it informs:** which diarizer and attachment method stay the default, and which are offered.
- **Expected result:** Who is faster and riskier with four voices, and word attachment preserves the most turns, as in the trial.
- **Builds on:** a [seven-recording trial](https://github.com/pomodorozhong/meeting-recap/blob/c714e05/docs/experiments/2026-11-01-synthetic-collection.md) in draft PR #31, which is **not on `main`**. Its `score_case.py` and `turn_order.py` at `c714e05` define the metrics carried over.

## Plan

- **Input:** all 17 hash-verified mono fixtures in the collection at `4c8c2f0`: fourteen independent scripts with one to four speakers, two remixes reported separately, and digital silence.
- **Assumptions:** one M2 Pro with 16 GB, serial local inference. Generated timestamps and identities are known intended references, not listener judgments.

| Run ID | Model and pinned version | Settings |
| --- | --- | --- |
| `sortformer` | Pinned Sortformer | Every recording |
| `who` | Pinned Who int8 | Every recording |
| `community`, `community-count` | Pinned Community-1 FluidAudio port | Automatic and known speaker count, on onboarding, tabletop and committee |
| `lseend-*` | Four pinned LS-EEND variants | Same three calls |

Speaker-time error is one-to-one, with overlap and no collar, meaning no tolerance around turn boundaries. Attachment gives each piece of recognized text a speaker label: word-level attachment labels each word by the speaker active during it, segment attachment labels each recognizer segment by the speaker who overlaps it most, and line-end attachment labels each segment by the speaker active at its end, as HushScribe does. All three methods go through the skill's known-turn evaluator (`review.py known` at `4c8c2f0`, 30 s windows, `ref-CASE` / `eval-CASE`), with no listening session or clip selection. Overlap, attenuated audio, label counts and the four-voice subset are checked separately.

### Changes to the plan

On the unmerged branch `codex/expanded-call-benchmark`, the criteria were committed in `e5f17b3`, before `e5a2db9`, the first commit that recorded speaker results. Git shows when text was committed, not when a run happened, so this doesn't show that the criteria came before the runs. Their wording was later edited to read against `main`; no threshold or rule changed.

A speaker-count correction was committed in `f62eb98`, also before any speaker result was recorded: the English committee script has **three** voices, so it keeps its actual count in the known-count condition, and the four-voice English tabletop was added so a four-voice English test is present. This follows fixture metadata, not predictions.

On 2026-11-03, after the runs, this summary was split out of one write-up covering every question, so that each question has its own summary and decision. No result changed. Nothing was rerun for the split.

## Results

### Speaker identity and timing

Speaker-time error is (missed + false-alarm + confused speaker-seconds) / reference speaker-seconds, pooled only over independent scripts in each row. Lower is better. Mapping is one-to-one optimal per file, overlap included, zero collar. Scripted turn intervals include pauses within TTS utterances, so time error also penalizes some valid silence detection.

| Script speakers | Independent calls | Sortformer | Who int8 |
| ---: | ---: | ---: | ---: |
| 1 | 2 | 12.06% | 7.89% |
| 2 | 4 | 5.66% | 2.74% |
| 3 | 5 | 10.51% | 3.34% |
| 4 | 3 | **9.94%** | 26.86% |

- **Merged speakers:** Who produced three labels for four speakers on all three clean four-voice calls.
- **Split speakers:** the known one-voice stocktake split into two labels with Who, as it did in the trial (28.7% versus Sortformer 11.2%). The three-person planning call split into four labels with both. Sortformer also split voices on scheduling and design.
- **Overlap reverses the clean result:** on the matched four-person overlap mix both found four labels, and Who had 13.6% error versus Sortformer 20.4%. The trial's overlap mix favored Sortformer (12.1% versus 25.2%).
- **Attenuated audio:** on the attenuated handoff, Who kept its advantage (4.9% versus 15.0%).
- **Silence:** neither emitted speech on digital silence, so a percentage error there is undefined.

Who's better aggregate on one through three voices doesn't predict every recording.

### Other diarizers

In the three-case sweep, Sortformer beat all four LS-EEND variants and both Community-1 settings on each call. Community-1's speaker-time error with automatic and known speaker count was 62.7% and 51.2% on onboarding, 54.6% and 26.1% on tabletop, and 70.9% for both on committee. On committee both settings returned just one of three voices. LS-EEND AMI beat Who on onboarding (18.2% versus 41.8%), but trailed Sortformer (13.8%). These results concern the pinned FluidAudio ports, not the original gated pyannote implementation.

### Attachment

The skill evaluated 16 non-silent recorded mixes, with no excluded clips. A turn is recovered when it comes out in the script's order. A whole clip is a 30-second window where every turn is recovered and no extra person or turn appears. Higher is better. Across the 14 independent scripts:

| Recognizer + diarizer | Word | Segment | Line-end | Out of |
| --- | ---: | ---: | ---: | ---: |
| Full Whisper + Sortformer, turns | **258** | 254 | 252 | 270 |
| Full Whisper + Sortformer, whole clips | **47** | 43 | 40 | 61 |
| Full Whisper + Who, turns | 250 | 244 | 243 | 270 |
| Full Whisper + Who, whole clips | 46 | 41 | 40 | 61 |

For Breeze, the skill refused word-level attachment on three English recordings, with each diarizer, because Breeze's output had text but no word timestamps. Comparing like with like on the other 11 scripts, word, segment and line-end attachment recovered 192, 191 and 189 of 204 turns with Sortformer, and 185, 185 and 182 with Who.

On the planning call, full Whisper + Sortformer labeled 1,355/1,385 characters correctly at ASR word times (97.8%), but only 1,259/1,314 aligned characters in the delivered transcript (95.8%). With Who the figures were 1,360/1,385 (98.2%) and 1,266/1,314 (96.3%). As in the pipeline's [November 1 baseline](../../experiments/pipelines/whisper-sortformer/README.md) on the earlier planning audio, Who scored slightly above Sortformer, and both scored lower in the delivered transcript than at word times.

**Limits.** Known-turn scores match labels to speakers separately for each run, then count turns that come out in the right order. They don't measure speaker error across the whole call. The word score lets several labels count as one person, so it can miss one person being split across two labels. The speaker-time score can't miss that. These results don't extend to real rooms, longer meetings or user-confirmed speaker identity.

## Runtime and memory

One inference process ran at a time on the M2 Pro with 16 GB, measured with `/usr/bin/time -l`, with the desktop in normal use. These are individual observations on this machine, not latency guarantees.

Across all 17 standalone diarizer runs, Who took 9.34 s in total (median 0.57 s; peak 0.275 GB) versus Sortformer 888.55 s (median 33.03 s; peak 0.847 GB), about 95× less total time. A separate Turbo + Who pipeline run on onboarding had a 20.77 s Who load and 0.37 s of inference, so these summaries don't guarantee a subsecond cold start.

## Decision

Keep Sortformer with word-level attachment as the default. Offer Who when speed matters more than speaker accuracy, especially with one to three speakers. Who's merged speakers on clean four-person calls decided this, despite its speed and lower error on fewer voices.

Editing `speakers.json` can't undo that failure, because it can merge labels but not split one. If a run shows fewer labels than the people who spoke, rerun with Sortformer. A matching count doesn't prove the labels are right: on the four-person overlap mix, both diarizers found four labels and still had 13.6% and 20.4% speaker-time error. This count check follows from these results, but wasn't tested as a procedure. See decision 13.

## Open questions

This experiment can't explain why a result changed. Two recordings are identical to the seven-recording trial's, so they check that the models repeat their results. Other recordings have new voices or remixes, so they check whether the trial's findings hold on different audio. But unrelated calls differ in voices, overlap and script all at once, so when results differ, we can't tell which of those caused it. For example, Sortformer won the trial's four-person overlap mix and Who won this one, and we don't know why.

All of this is synthetic audio. Before changing the default diarizer, check its speaker labels on real calls, using the private recordings a person has listened to.

## Where this ran

- **Code:** the collection is the one merged in #32 (`4c8c2f0`). The runs used development commits based on it, which are not on `main`. `main` holds the same runners in [`experiments/synthetic-call`](../../experiments/synthetic-call/README.md#compare-the-pipeline-on-this-collection).
- **Models and weights:** the revisions in [`pins.py`](../../experiments/pipelines/whisper-sortformer/pins.py) and [`alternative-diarizers.json`](../../experiments/synthetic-call/reference/alternative-diarizers.json).
- **Machine:** one M2 Pro with 16 GB, one inference process at a time.
- **Kept outside the repository:** raw calls and predictions, under benchmark ID `expanded-pipeline-20261102`. Public results contain counts and digests only.
