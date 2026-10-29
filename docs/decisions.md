# Decisions

Each decision gives what was decided and where the reasoning is. A later decision that replaces one says so, and the old entry is marked replaced rather than deleted. Status and open questions are in [README.md](README.md).

1. **Stop testing models for this kind of call** (2026-10-24). Whisper Large v3 with Chinese forced plus Sortformer was good enough on a three-person online Chinese + English call. See [both full recordings](experiments/2026-10-24-full-recordings.md).
2. **Pipeline candidate** (2026-10-24): Whisper Large v3 (Chinese forced) or Breeze-ASR-25, Sortformer, labels attached by overlap per word, a naming step that can merge labels, Traditional script output. See [experiments](experiments/README.md).
3. **Summaries and the other catalogue features are separate questions** (2026-10-24).
4. **Experiments run through the `meeting-experiment-review` skill** (2026-10-29): private dataset outside Git (`$MEETING_REVIEW_DATA`), a public summary in `docs/experiments/` committed before the first run, and a code snapshot per experiment so the live scripts carry no options kept only for old experiments.
5. **Repository layout** (2026-10-29, [#8](https://github.com/pomodorozhong/meeting-recap/issues/8)):
   - `experiments/<name>/` holds one self-contained experiment each: its code, pinned dependencies, and a README or summary link saying how to run it. Nothing outside the folder imports from it, and it never holds private data.
   - `experiments/pipelines/<name>/` holds candidate pipelines for saved recordings, under the same rules. Several can coexist while they are compared.
   - `app/` is the root of the final app. Once one pipeline is settled, the app gets its own copy of it, rebuilt as the app's code and dependencies; it does not depend on anything in `experiments/`. The experiment stays as the record its summary cites.
   - Decisions go in this file, one numbered entry each, rather than one file per decision: the project is small, and a single list is easier to read and keep current.
