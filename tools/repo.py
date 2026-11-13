"""Read repository files from Git's index or the working directory. Python 3.8+, standard library only.

Both trees expose `paths()` (POSIX paths relative to the root) and `read(path)`
(UTF-8 text). A missing path raises ValueError or OSError.
"""

import os
from pathlib import Path
import subprocess


def git(root, *args):
    """Run Git in `root` and return stdout bytes; raise ValueError with Git's message on failure."""
    result = subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


class IndexTree:
    """Files as staged in Git's index."""

    def __init__(self, root):
        self.root = Path(root)

    def paths(self):
        return sorted(p for p in git(self.root, "ls-files", "--cached", "-z").decode("utf-8").split("\0") if p)

    def read(self, path):
        return git(self.root, "show", ":" + path).decode("utf-8")


class WorkingTree:
    """Files in the working directory, including untracked ones."""

    def __init__(self, root):
        self.root = Path(root)

    def paths(self):
        result = []
        for directory, subdirectories, files in os.walk(str(self.root)):
            subdirectories[:] = [d for d in subdirectories if d != ".git"]
            base = Path(directory).relative_to(self.root)
            result.extend((base / name).as_posix() for name in files)
        return sorted(result)

    def read(self, path):
        return (self.root / path).read_bytes().decode("utf-8")
