"""Exercise the Git index and working-directory tree adapters against real Git."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("repo", Path(__file__).with_name("repo.py"))
repo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repo)


class Trees(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git("init", "-q")
        self.write("skills/example/SKILL.md", "staged\n")
        self.git("add", ".")
        self.index, self.working = repo.IndexTree(self.root), repo.WorkingTree(self.root)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args])

    def write(self, path, text):
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_text(text)

    def test_index_reads_staged_content_and_working_reads_files(self):
        self.write("skills/example/SKILL.md", "unstaged\n")
        self.assertEqual(self.index.read("skills/example/SKILL.md"), "staged\n")
        self.assertEqual(self.working.read("skills/example/SKILL.md"), "unstaged\n")

    def test_untracked_files_are_only_in_the_working_tree(self):
        self.write("docs/skills/new.md", "new\n")
        self.assertNotIn("docs/skills/new.md", self.index.paths())
        self.assertIn("docs/skills/new.md", self.working.paths())

    def test_staged_deletion_leaves_the_index(self):
        self.git("rm", "-q", "--cached", "skills/example/SKILL.md")
        self.assertNotIn("skills/example/SKILL.md", self.index.paths())
        self.assertIn("skills/example/SKILL.md", self.working.paths())

    def test_ignored_and_deleted_files_are_not_working_paths(self):
        self.write(".gitignore", "scratch/\n")
        self.write("scratch/docs.md", "ignored\n")
        self.git("add", ".gitignore")
        (self.root / "skills/example/SKILL.md").unlink()
        self.assertEqual(self.working.paths(), [".gitignore"])

    def test_git_metadata_is_not_a_working_path(self):
        self.assertFalse([p for p in self.working.paths() if p.startswith(".git/")])

    def test_missing_paths_raise(self):
        for tree in (self.index, self.working):
            with self.subTest(tree=type(tree).__name__):
                with self.assertRaises((ValueError, OSError)):
                    tree.read("missing.md")

    def test_git_returns_text(self):
        self.assertEqual(repo.git(self.root, "show", ":skills/example/SKILL.md"), "staged\n")

    def test_git_errors_carry_git_messages(self):
        with self.assertRaises(ValueError) as raised:
            repo.git(self.root, "rev-parse", "--verify", "no-such-ref")
        self.assertIn("fatal:", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
