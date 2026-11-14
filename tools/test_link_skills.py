"""Exercise the link-skills internal skill's script in temporary folders."""

import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / ".agents/skills/link-skills/scripts/link_skills.py"
SPEC = importlib.util.spec_from_file_location("link_skills", SCRIPT)
linker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(linker)


class Sync(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.root))
        self.repo, self.hub, self.agent = self.root / "repo", self.root / "hub", self.root / "agent"
        for name in ("alpha", "beta"):
            self.add_skill(name)

    def add_skill(self, name):
        (self.repo / "skills" / name).mkdir(parents=True)
        (self.repo / "skills" / name / "SKILL.md").write_text("---\nname: {}\n---\n".format(name))

    def sync(self, dry_run=False):
        return linker.sync(self.repo, self.hub, [self.agent], dry_run)

    def test_links_each_skill_through_the_hub_so_edits_are_live(self):
        actions, warnings = self.sync()
        self.assertEqual((len(actions), warnings), (4, []))
        self.assertEqual(linker.link_target(self.hub / "alpha"), self.repo / "skills/alpha")
        self.assertEqual(linker.link_target(self.agent / "alpha"), self.hub / "alpha")
        (self.repo / "skills/alpha/SKILL.md").write_text("edited")
        self.assertEqual((self.agent / "alpha/SKILL.md").read_text(), "edited")
        self.assertEqual(self.sync(), ([], []))

    def test_removes_links_left_by_a_renamed_skill(self):
        self.sync()
        (self.repo / "skills/beta").rename(self.repo / "skills/gamma")
        actions, warnings = self.sync()
        self.assertEqual(warnings, [])
        self.assertFalse(os.path.lexists(str(self.hub / "beta")))
        self.assertFalse(os.path.lexists(str(self.agent / "beta")))
        self.assertEqual(linker.link_target(self.agent / "gamma"), self.hub / "gamma")

    def test_leaves_real_folders_and_foreign_links_in_place(self):
        (self.hub / "alpha").mkdir(parents=True)
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        os.symlink(str(elsewhere), str(self.hub / "beta"))
        os.symlink(str(self.root / "gone"), str(self.hub / "foreign"))
        _, warnings = self.sync()
        self.assertEqual(len(warnings), 2)
        self.assertTrue((self.hub / "alpha").is_dir() and not (self.hub / "alpha").is_symlink())
        self.assertEqual(linker.link_target(self.hub / "beta"), elsewhere)
        self.assertTrue(os.path.lexists(str(self.hub / "foreign")))

    def test_dry_run_reports_without_changing_anything(self):
        actions, _ = self.sync(dry_run=True)
        self.assertEqual(len(actions), 4)
        self.assertFalse(self.hub.exists() or self.agent.exists())


if __name__ == "__main__":
    unittest.main()
