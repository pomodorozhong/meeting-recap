"""Restore FluidAudio model folders from immutable revisions, without replacing existing data."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile
from urllib.parse import quote
from urllib.request import urlopen

import pins


def download(repo, revision, relative, destination):
    url = f"https://huggingface.co/{repo}/resolve/{revision}/{quote(relative, safe='/')}"
    with urlopen(url, timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def check(name, root=None):
    spec = pins.FLUID_MODELS[name]
    folder = (Path(root) if root is not None else pins.SORTFORMER_MODELS.parent) / name
    if not folder.is_dir() or pins.tree_sha256(folder) != spec["tree_sha256"]:
        raise ValueError(f"missing or changed {name} weights; preserve any existing folder elsewhere, "
                         f"then run weights.py setup {name}")
    return folder


def install(name, root=None):
    spec = pins.FLUID_MODELS[name]
    parent = Path(root) if root is not None else pins.SORTFORMER_MODELS.parent
    destination = parent / name
    if destination.exists() or destination.is_symlink():
        return check(name, parent)
    parent.mkdir(parents=True, exist_ok=True)
    # Stage on the same filesystem. Failed downloads never become a usable model folder.
    with tempfile.TemporaryDirectory(prefix=f".{name}-", dir=parent) as temporary:
        staged = Path(temporary) / name
        staged.mkdir()
        for relative, expected in spec["files"].items():
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError(f"invalid model path: {relative}")
            target = staged / path
            target.parent.mkdir(parents=True, exist_ok=True)
            download(spec["repo"], spec["revision"], relative, target)
            with target.open("rb") as handle:
                actual = hashlib.file_digest(handle, "sha256").hexdigest()
            if actual != expected:
                raise ValueError(f"download digest mismatch: {name}/{relative}")
        check(name, Path(temporary))
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"model folder appeared during download: {destination}")
        staged.rename(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["setup", "check"])
    parser.add_argument("models", nargs="+", choices=sorted(pins.FLUID_MODELS))
    parser.add_argument("--root", type=Path, help="model-cache parent; defaults to FluidAudio's cache")
    args = parser.parse_args()
    operation = install if args.command == "setup" else check
    for name in args.models:
        folder = operation(name, args.root)
        print(f"{name}: {pins.FLUID_MODELS[name]['tree_sha256']} ({folder})")


if __name__ == "__main__":
    main()
