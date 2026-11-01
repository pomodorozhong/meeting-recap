"""Export or verify the small, synthetic-only evidence bundle for the published 70-cell report."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from score_actions import EXTRAS, HERE, MODES, SCRIPTS, evaluate
from score_speakers import load, sha256

BUNDLE = HERE / "reference/action-replay.json"
REPORT = HERE.parents[1] / "docs/experiments/2026-11-01-action-evidence-results.json"
VERDICTS = HERE / "reference/action-verdicts.json"


def required_files():
    """Explicit allowlist: no recordings, logs, environment dumps or arbitrary run files."""
    relative = ["case.json", "pipeline/stages.json", "large-pipeline/stages.json"]
    relative += [f"{mode}/{name}.json" for mode in (*MODES, *EXTRAS) for name in ("lines", "items")]
    relative += [f"{mode}/run.json" for mode in EXTRAS]
    return sorted(f"{script.stem}/{name}" for script in SCRIPTS.glob("*.json") for name in relative)


def export(results, destination):
    """Copy the original scoring bytes only after they reproduce the published report."""
    if evaluate(results) != load(REPORT):
        raise ValueError("source outputs do not reproduce the published report")
    files = {}
    for relative in required_files():
        data = (Path(results) / relative).read_bytes()
        files[relative] = {"sha256": hashlib.sha256(data).hexdigest(), "text": data.decode("utf-8")}
    bundle = {"schema": 1, "scoring_source_commit": "cac52ea83f8101b11dca8b2d0ab2357a9738dae6",
              "report_sha256": sha256(REPORT), "verdicts_sha256": sha256(VERDICTS), "files": files}
    with Path(destination).open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n")


def replay(bundle_path=BUNDLE):
    bundle = load(bundle_path)
    if bundle.get("schema") != 1 or set(bundle.get("files", {})) != set(required_files()):
        raise ValueError("incomplete or unexpected replay files")
    if bundle["report_sha256"] != sha256(REPORT) or bundle["verdicts_sha256"] != sha256(VERDICTS):
        raise ValueError("report or verdicts changed since export")
    with tempfile.TemporaryDirectory(prefix="action-replay-") as temporary:
        root = Path(temporary)
        for relative, entry in bundle["files"].items():
            data = entry["text"].encode("utf-8")
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError(f"changed replay file: {relative}")
            path = root / relative  # The exact allowlist above excludes traversal and absolute paths.
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        result = evaluate(root)
    if result != load(REPORT):
        raise ValueError("replayed scores or recorded timings differ from the published report")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("export", help="copy the allowlisted original synthetic outputs")
    p.add_argument("results", type=Path)
    p.add_argument("destination", type=Path, help="new JSON file; never overwrites an existing bundle")
    p = commands.add_parser("check", help="verify all published scores and recorded timings without models")
    p.add_argument("bundle", nargs="?", type=Path, default=BUNDLE)
    args = parser.parse_args()
    if args.command == "export":
        export(args.results, args.destination)
    else:
        result = replay(args.bundle)
        cells = sum(len(modes) for modes in result["cases"].values())
        print(f"PASS: {cells} case/condition results and all recorded timings match the published report")


if __name__ == "__main__":
    main()
