"""Download (`download`) or list (`list`) the pinned models in run.py's MODELS table."""
import sys

from run import MODELS


def main(command):
    if command == "list":
        print(" ".join(MODELS))
    elif command == "download":
        from huggingface_hub import snapshot_download

        for repo, revision, _ in MODELS.values():
            print(repo, snapshot_download(repo_id=repo, revision=revision))
    else:
        sys.exit("usage: models.py download|list")


if __name__ == "__main__":
    main(*sys.argv[1:2] or [""])
