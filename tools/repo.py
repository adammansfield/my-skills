"""Read repository files from Git's index or the working directory. Python 3.8+, standard library only.

Both trees expose `paths()` (POSIX paths relative to the root) and `read(path)`
(UTF-8 text). A missing path raises ValueError or OSError.
"""

from pathlib import Path
import subprocess


def git(root, *args):
    """Run Git in `root` and return stdout as UTF-8 text; raise ValueError with Git's message on failure."""
    result = subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout.decode("utf-8")


def git_list(root, *args):
    """Run a Git listing command with `-z` and return its entries."""
    return [entry for entry in git(root, *args, "-z").split("\0") if entry]


def toplevel(directory):
    """Return the root of the Git checkout containing `directory`."""
    return Path(git(directory, "rev-parse", "--show-toplevel").strip())


class IndexTree:
    """Files as staged in Git's index."""

    def __init__(self, root):
        self.root = Path(root)

    def paths(self):
        return sorted(git_list(self.root, "ls-files", "--cached"))

    def read(self, path):
        return git(self.root, "show", ":" + path)


class WorkingTree:
    """Files in the working directory: tracked and untracked, excluding ignored and deleted files."""

    def __init__(self, root):
        self.root = Path(root)

    def paths(self):
        listed = git_list(self.root, "ls-files", "--cached", "--others", "--exclude-standard")
        return sorted({p for p in listed if (self.root / p).is_file()})

    def read(self, path):
        return (self.root / path).read_bytes().decode("utf-8")
