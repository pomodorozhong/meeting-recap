# whisper-sortformer pipeline

The first end-to-end pipeline for a saved recording ([#28](https://github.com/pomodorozhong/meeting-recap/issues/28)): audio → Whisper Large v3 (Chinese forced, word timestamps) and Sortformer → speaker labels attached per word → an editable speaker mapping → a Traditional Chinese Markdown transcript → a local recap of topics, decisions, action items, proposals and open questions, each with transcript timestamps.

It assembles the baseline from [decision 1](../../../docs/decisions.md) without further model comparison. It is made for an online call with two or three speakers in Mandarin with English terms. Everything runs locally on an M2 Pro with 16 GB of memory.

## Setup (once, needs the network)

From the repository root:

```bash
cd experiments/pipelines/whisper-sortformer
swift build -c release --product fluidaudiocli
cd -
uv run --project experiments/pipelines/whisper-sortformer experiments/pipelines/whisper-sortformer/recap.py setup
```

- `swift build` takes about two and a half minutes. It builds FluidAudio's `fluidaudiocli` at the pinned revision into this folder's `.build/`.
- `setup` downloads the two pinned Hugging Face snapshots (Whisper about 3 GB, Qwen about 5.6 GB) to the Hugging Face cache. It also runs Sortformer once on generated silence, so FluidAudio downloads its models to `~/Library/Application Support/FluidAudio/Models`.
- `ffmpeg` and `ffprobe` must be on `PATH` (`brew install ffmpeg`).

## Run (offline)

```bash
uv run --project experiments/pipelines/whisper-sortformer experiments/pipelines/whisper-sortformer/recap.py run recording.m4a ~/meeting-notes/2026-11-01-call
```

- **Input:** any file ffmpeg reads.
- **Output folder:** must be new or empty, and outside this Git checkout. An existing run is never replaced.
- **Offline:** both Python model stages run with `HF_HUB_OFFLINE=1`, so they fail rather than download a different revision. Sortformer loads FluidAudio's cached models.
- **Order:** stages run one after another. Each model runs in its own process, so its memory is freed before the next model loads.
- **`--no-summary`:** stops after the transcript.

| Stage | Writes | What it does |
| --- | --- | --- |
| `convert` | `audio.wav` | ffmpeg to 16 kHz mono 32-bit float, keeping the time origin |
| `asr` | `asr.json` | Whisper Large v3 through `mlx-whisper`: `language=zh`, word timestamps, `condition_on_previous_text=False` |
| `diarize` | `sortformer.raw.json`, `diarization.json` | FluidAudio Sortformer (`fluidaudiocli sortformer`), converted to segments |
| `attach` | `turns.json`, `speakers.json` | Each word gets the label it overlaps most (else the nearest within 1 s). Same-label words less than 1 s apart form one turn |
| `transcript` | `transcript.md` | Speaker names applied, OpenCC `s2tw` to Traditional characters, one `**[HH:MM:SS] Name:**` paragraph per turn |
| `summary` | `summary.json`, `summary.md` | Qwen3.5 9B through `mlx-lm`, described below |

`run.json` records the input's name and SHA-256, the code commit, the pinned models and the machine. `stages.json` records each stage's status, wall time, peak memory and output digests, or its error. `logs/` holds each process's output and `/usr/bin/time -l` report.

### Names and merging speakers

`speakers.json` maps each diarization label to a name. Defaults are `Speaker A`, `B`, `C` in order of first appearance, and `Unknown speaker` for words outside every diarization segment. Edit the names, then rebuild the transcript without rerunning any model:

```json
{"labels": {"Speaker_0": "Speaker A", "Speaker_2": "Speaker B", "Speaker_3": "Speaker B"}}
```

```bash
uv run --project experiments/pipelines/whisper-sortformer experiments/pipelines/whisper-sortformer/recap.py render ~/meeting-notes/2026-11-01-call
```

Giving two labels one name merges them, as when Sortformer splits one voice across two labels. `render` refuses a mapping that leaves a label out. A later `run --resume` never overwrites an edited `speakers.json`.

The recap names speakers as they were when it ran. `render` says when the names have changed since. Run `summarize OUT --replace` to rewrite `summary.md` with the new names.

### Recap

The transcript goes to the model as `[HH:MM:SS] Name: text` lines, split into chunks of about 6,000 characters (about 15 minutes of speech), never mid-line.

**Prompts and decoding.** Each chunk gets one prompt: [`pipeline.extract_prompt`](pipeline.py). A recording with several chunks gets one more prompt that merges the chunk notes. Decoding is greedy with thinking disabled, up to 4,096 tokens per reply.

**What the model is told:**
- Write in Traditional Chinese and keep English terms.
- Keep decisions apart from proposals and open questions.
- Fill an owner or deadline only when the transcript states it.
- Cite the timestamps that support each point.

**Checks after the reply.** The pipeline keeps only cited timestamps that begin a transcript line. `summary.md` marks an item with no remaining support as "(no supporting timestamp)". `summary.json` keeps every raw reply, the parsed notes and the counts of dropped evidence.

**Limits.** The recap is a first draft. Nothing checks that a cited line actually says what the item claims. Read the cited lines before relying on a decision or an action item.

## Failures and reruns

- **A failed stage:** the run exits nonzero with `error: stage <name> failed: …` and the last log lines. `stages.json` records the failure, and every completed output stays. Fix the cause and rerun with `--resume`. It reruns only stages that aren't recorded as completed with unchanged output digests, and it refuses a different recording.
- **Sortformer:** `fluidaudiocli` exits 0 even when it fails, so the diarize stage treats a missing output file as a failure.
- **Partial files:** outputs are written beside their destination and renamed into place, so a crash leaves no half-written file under its final name.
- **Summary refusal:** `summarize` refuses to replace `summary.md` unless given `--replace`.

## Measurement

Each stage process runs under `/usr/bin/time -l`. `stages.json` records:
- **`wall_seconds`:** wall time.
- **`max_rss_bytes`:** maximum resident set size.
- **`peak_footprint_bytes`:** the peak memory footprint macOS reports.

Neither of the last two counts Metal buffers fully. For an MLX model they can show under 1 GB while the GPU holds about 5 GB of weights. The MLX stages therefore also record **`mlx_peak_bytes`**, MLX's own peak allocation; read memory for those stages from that field. The `total` entry is the wall time of that invocation only, so a resumed run counts just the stages it ran.

## Pins

| Part | Pin |
| --- | --- |
| Whisper | [`mlx-community/whisper-large-v3-mlx`](https://huggingface.co/mlx-community/whisper-large-v3-mlx) at `49e6aa286ad60c14352c404340ded53710378a11`, through `mlx-whisper` 0.4.2 |
| Sortformer | FluidAudio `ea500621819cadc46d6212af44624f2b45ab3240` (`Package.swift`, `Package.resolved`); model `Sortformer_v2.1.mlmodelc` as in [docs/runners.md](../../../docs/runners.md) |
| Recap | [`mlx-community/Qwen3.5-9B-4bit`](https://huggingface.co/mlx-community/Qwen3.5-9B-4bit) at `8b2b98c00a6b4d291155e4890773ca8f769aee53` (Apache-2.0), through `mlx-lm` 0.32.2 |
| Python packages | `uv.lock` |
| Script conversion | `opencc-python-reimplemented` 0.1.7, `s2tw` |

Python dependencies are in this folder's uv project. Rerun `uv lock` here after changing them.

## Tests

From the repository root, with generated audio and the model processes replaced by fakes:

```bash
uv run --project experiments/pipelines/whisper-sortformer python -m unittest discover -s tests/pipelines -t tests/pipelines
```

## Baseline on the synthetic call (2026-11-01)

The [synthetic call](../../synthetic-call/README.md) (seed 7, 5:29, three speakers, 73 turns) ran through every stage with `run`, on an M2 Pro with 16 GB of memory running macOS 26.6.2. Nothing else heavy was running.

### Time and memory

| Stage | Wall time | × audio length | Peak memory |
| --- | --- | --- | --- |
| convert | 0.2 s | — | — |
| asr | 47 s | 0.14× | 3.96 GB (MLX) |
| diarize | 136 s | 0.41× | 0.79 GB footprint, 1.06 GB RSS |
| attach + transcript | 0.1 s | — | — |
| summary (one chunk, about 2,000 prompt tokens) | 99 s | — | 6.71 GB (MLX) |
| **total** | **283 s** | **0.86×** | **6.71 GB**, one model at a time |

- **Matches earlier runs:** Sortformer's 0.41× matches its 2026-10-24 runs on 87 minutes of a real call.
- **Projection, not measured:** an hour-long call would take about 33 minutes before the summary (0.55×). The summary adds about one prompt per 15 minutes plus a merge prompt.

### Quality

| Measure | Result | How |
| --- | --- | --- |
| Speaker agreement, diarization alone | 98.2% of characters | Each Whisper word's time is checked against the known turns, with the best label mapping |
| Speaker agreement, in the transcript | 95.1% of 1,317 aligned characters | Transcript characters are aligned to the script's text (OpenCC `t2s`, punctuation dropped), so text Whisper placed in the wrong turn counts as an error |
| Script characters recovered | 1,317 of 1,377 aligned | Same alignment; the rest are ASR errors |
| Labels | 4, for 3 speakers | The fourth holds 2 characters; renaming it in `speakers.json` merges it |
| Recap evidence | 6 topics, 7 decisions, 10 action items, 3 proposals, 2 open questions; every item kept a valid timestamp | Read by hand against the script, not scored |

### Issues found, most important first

The point of this baseline is to see where the whole pipeline loses most before optimizing any part. Each issue needs its own measurement on a real recording before it is fixed.

1. **Words cross turn boundaries.** Whisper's word times drift at turn changes, so a reply's first character often stays with the previous speaker (「聽」 then 「得到」). This costs about 3 points of speaker agreement on top of diarization's own errors, and it is visible on almost every short reply. Candidate fixes: split turns at Whisper segment or punctuation boundaries that lie near a diarization change, or align words with a separate forced aligner.
2. **The recap mixes assignments into decisions.** Who does what appears both as decisions and as action items, two action items repeat one task, and one action item's owner is doubtful. Every item cites real lines, but whether those lines support the item is checked only by reading. Only the private-recording review can say whether this matters.
3. **Runtime is dominated by Sortformer** at 0.41×, three times Whisper's time. ASR and diarization don't depend on each other and fit in memory together (about 5 GB), so running them in parallel is the obvious first optimization. It is deliberately not done until a real recording confirms the baseline.
4. **ASR errors and punctuation.** Homophones land in the transcript and the recap (「分頁」 as 「糞頁」, 「時間」 as 「實踐」). Whisper writes mostly half-width punctuation (34 of 38 marks), which reads oddly in Chinese. `opencc-python-reimplemented` converts 「只有」 to 「隻有」 under both `s2tw` and `s2twp`.
5. **A spare speaker label** appears for a few characters. Naming handles it; nothing to change yet.

## Known limits

- **Speakers:** the speaker count is not set. Sortformer handles at most four speakers.
- **Overlaps:** overlapping speech goes to one speaker per word.
- **ASR runtime:** Whisper runs through MLX, not the WhisperKit CLI used on 2026-10-24. It has the same model weights but no VAD chunking, and long silences can still produce stray text.
- **Scope:** no live capture, GUI, or search.
