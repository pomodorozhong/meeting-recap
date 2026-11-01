# Action grounding probes

This is the first executable input pack for the [falsification plan](../../docs/experiments/2026-11-01-action-grounding-plan.md). It prepares 60 exact-text extraction cases and 36 single-candidate verifier controls without synthesis, model inference or user input. The [audit](../../docs/experiments/2026-11-01-action-evidence-review.md) explains why these controls are needed.

The six families have a frozen development/holdout split. Every family has the same ten transformations. `families.json` and `prepare.py` together define the complete fixtures; neither model receives the answer key. This is a controlled diagnostic suite. Template transformations do not become independent natural meetings.

## Prepare

Run from the repository root with standard-library Python. The destination must not exist and must be outside a Git checkout. Use a persistent external benchmark directory for actual inference; the temporary directory below is suitable for inspecting the design.

```bash
PROBES_PARENT=$(mktemp -d)
PROBES="$PROBES_PARENT/action-grounding"
python3 experiments/action-grounding/prepare.py "$PROBES"
```

Each extraction folder holds `lines.json` and `expected.json`. Each verification folder also holds `candidates.json`. The manifest records every source/input/key digest and explicitly says `prepared-not-run`. `L001`, `L002`, etc. in keys identify the first, second, etc. displayed input lines. Ten-second spacing guarantees unique timestamps in this pack. No actual audio timing is implied.

## Invoke existing baselines

These are example single-case commands for the planned runs, not instructions to expose expected answers. The pipeline must already have its pinned environment and models. Write each invocation to a fresh result directory, capture exit status, and enforce the plan's time limits in the future batch runner. Preserve failed outputs.

```bash
PIPE=experiments/pipelines/whisper-sortformer
CASE="$PROBES/extract/scanner/base"
RUN=$(mktemp -d)
HF_HUB_OFFLINE=1 /usr/bin/time -l -o "$RUN/stage.time" \
  uv run --locked --project "$PIPE" python "$PIPE/summary_stage.py" \
  "$CASE/lines.json" "$RUN/raw.json" --actions-only \
  > "$RUN/stage.log" 2>&1
```

Omit `--actions-only` for the original full-recap comparator. Use a separate result directory. For the verifier's known-good control, use the same pinned stage with one frozen candidate.

```bash
CASE="$PROBES/verify/scanner/positive"
RUN=$(mktemp -d)
HF_HUB_OFFLINE=1 /usr/bin/time -l -o "$RUN/stage.time" \
  uv run --locked --project "$PIPE" python "$PIPE/summary_stage.py" \
  "$CASE/lines.json" "$RUN/raw.json" --verify-actions "$CASE/candidates.json" \
  > "$RUN/stage.log" 2>&1
```

No module imports across experiment folders. The existing pipeline is invoked through its CLI. A model output is not automatically a score. Stage 0 evaluator calibration and separate transcript-support/intended-answer judgments in the plan must precede reporting model comparisons. There is no batch inference orchestrator or semantic scorer in this new folder yet, and no model result is claimed.

## Check the fixtures

```bash
uv run --no-project python -m unittest discover -s experiments/action-grounding/tests -v
```

Five tests check isolated field interventions, invariant and negative controls, unique evidence references, verifier controls, manifest digests and refusal to overwrite prior outputs or write them inside Git. They validate the fixture machinery, not a model's understanding of the conversations.
