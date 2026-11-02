# 2026-11-02: retest the saved-audio pipeline on the expanded collection

**Status:** planned.

## Question and decision

Do the [seven-recording results](https://github.com/pomodorozhong/meeting-recap/blob/c714e05/docs/experiments/2026-11-01-synthetic-collection.md) generalize? Specifically: is Turbo always as accurate and faster than full Whisper; does Breeze win on sparse speech; is Who faster but riskier with four voices; does word attachment preserve more turns; do clean transcripts rescue recap facts? Distinguish those claims from the [separate action recovery experiment](https://github.com/pomodorozhong/meeting-recap/blob/c714e05/docs/experiments/2026-11-01-action-evidence.md), whose prompts and reference labels are specific to that benchmark.

## Input and assumptions

Use all 17 hash-verified mono fixtures at source 4c8c2f0. Fourteen independent scripts (eight Mandarin including English terms, six English; one to four speakers). Report the two remixes and digital silence separately. The earlier collection has some of the same scripts, but synthesis/voices changed; only matching audio hashes are exact replications. One M2 Pro / 16 GB; serial local inference; generated text, timestamps and identities are known intended references, not listener judgments.

## Registered plan

- Verify the fixtures with the synthetic project's collection.py --check. Use fresh external results under benchmark ID expanded-pipeline-20261102. Preserve any failed cells. No listening session or clip selection; for turn order use review.py known at 4c8c2f0 (30 s windows), ref-CASE / eval-CASE.
- For each case, convert with the pipeline ffmpeg settings. Run the pinned MLX runners (word timestamps on, previous-text conditioning off, stock decoding) with full Whisper 49e6aa28, Turbo Q4 660c343b and Breeze 172151e3. Force the script's declared language; zh for controls. Also decode the six English inputs with the shipping zh-forced full model. Report English WER and Mandarin CER separately with score_transcripts.py; track latency, footprint, and text on silence. Expect English routing to improve WER. Keep Mandarin default; expose language explicitly if it wins.
- Run pinned Sortformer and Who on the same converted audio, score one-to-one speaker-time error with overlap and no collar. Compare all three attachment methods through the known-turn evaluator. Check overlap, attenuated audio, label counts, and four-voice subset separately. Check the earlier alternative-diarizer ranking on new clean four-voice onboarding and English committee using available pinned Community-1 and LS-EEND runners.
- Reapply the earlier five-second exact-zero splitter (250 ms context), with language-matched decoding on all qualifying calls. For unchanged audio reuse the unsplit result. Keep it experimental unless neither language regresses. Distinguish internal pause errors from pure silence.
- Run Qwen3.5 9B at 8b2b98c0 via the ordinary pipeline, and again from the exact turns, on onboarding and English audit. Compare these nine preregistered semantic checks: onboarding turns 9, 10, 12, 14–16 (account test owner/time; documentation owner/time; test access restored; production access still separate/unapproved); English audit turns 2, 3, 7, 8/11, 10 (corrected adapter total; usable cable count; scale fault unresolved; corrected booking; delivery expected, not received). Score full / partial / absent or wrong; use anonymous labels mapped to reference by overlap. Also audit reopened questions and unsupported details. This is targeted unblinded review of synthetic content; no claims about all action precision or recall.
- Repeat full, Turbo and Breeze on one short clean case and silence to check text repeatability. Measure wall time and process footprint; no caching a model across timed invocations. No tuning on the scored scripts. Keep a candidate only as an option when results vary by call. Do not extrapolate to real rooms, longer meetings, or user-confirmed speaker identity.

## Restart

Use the locked synthetic and pipeline projects, pipeline setup and Swift binaries in their READMEs; use the MLX run.py CLI with repo, language and pinned revision. The previous benchmark's score_case.py, turn_order.py and silence_split.py at c714e05 define the historical metrics. Use the new collection's language-aware transcript scorer. Store raw calls, predictions and individual judgments outside Git. Public results contain counts and digests only.

## Runtime and memory

Pending.

## Results and limits

Pending.

## Decision and open questions

Pending.
