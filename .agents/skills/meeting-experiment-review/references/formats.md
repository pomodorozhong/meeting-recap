# Dataset formats

## Layout

```
<dataset>/
  dataset.json                      {"format": "meeting-review-dataset", "version": 1}
  recordings/<id>/recording.json    id, sha256, duration_seconds, group, media
  recordings/<id>/source.<ext>
  runs/<id>/run.json                id, recording_id, model, status, artifacts{name: {path, sha256}}, config, runtime, notes[, parents]
  runs/<id>/<artifact>.<ext>
  sessions/<id>/session.json        the frozen plan
  sessions/<id>/events.jsonl        answer / close events, seq 1..n
  references/<id>.json              confirmed clips, excluded items, digests of session and events
                                    (or, from `review.py known` or `tracks`, a `source` with the known
                                    segments' digest, or each track's digest and the activity settings)
  evaluations/<id>/evaluation.json
  evaluations/<id>/report.md
```

IDs are 1–64 letters, digits, `_`, or `-`, starting with a letter or digit.

## `segments` artifact (diarization)

```json
[{"speaker_id": "0", "start_seconds": 1.2, "end_seconds": 4.8}]
```

Labels are only meaningful within one run. `__unassigned__` marks text with no overlapping speaker after attachment and never matches a person.

## `transcript` artifact (ASR)

WhisperKit report shape. `words` is needed for `attach.py --method word`.

```json
{"text": "...", "segments": [{"start": 0.0, "end": 5.1, "text": "...",
  "words": [{"word": "你", "start": 0.0, "end": 0.4}]}]}
```

Special tokens such as `<|zh|>` are stripped when attaching.

## Answer

```json
{"item_id": "c01", "state": "confirmed",
 "annotation": {"speaker_order": ["A", "B"], "allow_extra_turns": false},
 "feedback_text": "B starts mid-word"}
```

Transcript items use `"annotation": {"text": "..."}`. The page also sends `expected_revision` so two tabs cannot overwrite each other.

## Metric

`speaker_order_lcs`: for each clip (plus `padding_seconds` either side), the run's labels overlapping it by at least `min_overlap` seconds are collapsed into a turn sequence. Turns recovered is the longest common subsequence with the confirmed order; a clip is correct when every turn is recovered, no unexpected person appears, and there are no extra turns unless `allow_extra_turns` is set. The label-to-person mapping is either fitted to maximize the score (searches over at most 100 000 mappings) or supplied explicitly.
