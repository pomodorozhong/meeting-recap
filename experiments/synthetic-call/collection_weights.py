"""Restore the alternative diarizers' FluidAudio folders from pinned revisions, or check them."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from urllib.parse import quote
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
SOURCES = json.loads((HERE / "reference/alternative-diarizers.json").read_text())
FLUID_MODELS = Path.home() / "Library/Application Support/FluidAudio/Models"


def tree_sha256(folder):
    """The same digest as the pipeline's pins.tree_sha256: each relative path and file digest, in path order."""
    digest = hashlib.sha256()
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        with path.open("rb") as handle:
            digest.update(f"{path.relative_to(folder).as_posix()}\0{hashlib.file_digest(handle, 'sha256').hexdigest()}\n".encode())
    return digest.hexdigest()


def check(name, root):
    folder = root / name
    if not folder.is_dir() or tree_sha256(folder) != SOURCES[name]["tree_sha256"]:
        raise ValueError(f"missing or changed {name} weights in {root}; move any existing folder aside, "
                         f"then run collection_weights.py setup")
    return folder


def install(name, root):
    spec = SOURCES[name]
    destination = root / name
    if destination.exists() or destination.is_symlink():
        return check(name, root)
    root.mkdir(parents=True, exist_ok=True)
    # Stage on the same filesystem, so a failed download never becomes a usable model folder.
    with tempfile.TemporaryDirectory(prefix=f".{name}-", dir=root) as temporary:
        staged = Path(temporary) / name
        for relative, expected in spec["files"].items():
            target = staged / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://huggingface.co/{spec['repo']}/resolve/{spec['revision']}/{quote(relative, safe='/')}"
            with urlopen(url, timeout=60) as response, target.open("wb") as output:
                shutil.copyfileobj(response, output)
            with target.open("rb") as handle:
                if hashlib.file_digest(handle, "sha256").hexdigest() != expected:
                    raise ValueError(f"download digest mismatch: {name}/{relative}")
        check(name, Path(temporary))
        staged.rename(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "check"))
    parser.add_argument("--root", type=Path, default=FLUID_MODELS, help="model-cache parent; defaults to FluidAudio's")
    args = parser.parse_args()
    for name in SOURCES:
        folder = (install if args.command == "setup" else check)(name, args.root)
        print(f"{name}: {SOURCES[name]['tree_sha256']} ({folder})")


if __name__ == "__main__":
    main()
