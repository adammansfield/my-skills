"""Exercise the metadata guardrail and its staged-file behavior using only stdlib."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("check_skills", Path(__file__).with_name("check_skills.py"))
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

SKILL = '''---
name: example
description: Use when the user requests "example".
---

Example instructions.
'''
UI = '''interface:
  display_name: "Example"
  short_description: "An example skill for metadata validation"
policy:
  allow_implicit_invocation: true
'''
DOC = '''# Example

An example skill.

## Invocation

Use the example trigger.
'''
UPSTREAM = '''
## Upstream

### Sources

[example](https://github.com/mattpocock/skills/blob/main/example/SKILL.md).

### Diff

[baseline](https://github.com/mattpocock/skills/commit/{})
'''.format("a" * 40)


class FakeTree:
    """An in-memory tree satisfying the repo tree interface."""

    def __init__(self, files):
        self.files = files

    def paths(self):
        return sorted(self.files)

    def read(self, path):
        if path not in self.files:
            raise OSError("missing " + path)
        return self.files[path]


WRAPPER = SKILL[:SKILL.index("\n---", 3) + 4] + "\n\nRead and follow `.agents/skills/example/SKILL.md` from this repository's root.\n"


class MetadataChecks(unittest.TestCase):
    def setUp(self):
        self.files = {"skills/example/SKILL.md": SKILL, "skills/example/agents/openai.yaml": UI}

    def check(self):
        return checker.check(FakeTree(self.files))

    def edit(self, path, old, new):
        self.files[path] = self.files[path].replace(old, new)

    def shared_skill(self):
        self.files.update({".agents/skills/example/SKILL.md": SKILL,
                           ".agents/skills/example/agents/openai.yaml": UI,
                           ".claude/skills/example/SKILL.md": WRAPPER})

    def test_valid_model_callable_skill(self):
        self.assertEqual(self.check(), [])

    def test_original_and_upstream_docs_are_valid(self):
        for text in [DOC, DOC + UPSTREAM]:
            with self.subTest(text=text):
                self.files["docs/skills/example.md"] = text
                self.assertEqual(self.check(), [])

    def test_doc_contract_errors_name_the_doc(self):
        # The full contract is covered by test_intent_docs; this checks the checker reports it.
        self.files["docs/skills/example.md"] = DOC + "\n## Upstream\n\n### Notes\n\nUntracked.\n"
        errors = self.check()
        self.assertIn("docs/skills/example.md:", errors[0])
        self.assertIn("### Sources", errors[0])

    def test_explicit_only_requires_matching_host_policies(self):
        self.edit("skills/example/SKILL.md", "name: example", "name: example\ndisable-model-invocation: true")
        self.assertIn("opposite", self.check()[0])
        self.edit("skills/example/agents/openai.yaml", "true", "false")
        self.assertEqual(self.check(), [])

    def test_name_must_match_directory(self):
        self.edit("skills/example/SKILL.md", "name: example", "name: wrong-name")
        self.assertIn("name must match", self.check()[0])

    def test_quoted_boolean_is_not_boolean(self):
        self.edit("skills/example/agents/openai.yaml", "true", '"true"')
        self.assertIn("opposite", self.check()[0])

    def test_missing_ui_is_reported(self):
        del self.files["skills/example/agents/openai.yaml"]
        self.assertTrue(self.check())

    def test_short_description_length_is_checked(self):
        self.edit("skills/example/agents/openai.yaml", "An example skill for metadata validation", "Too short")
        self.assertIn("25–64", self.check()[0])

    def test_duplicate_metadata_is_rejected(self):
        self.files["skills/example/agents/openai.yaml"] += "policy:\n  allow_implicit_invocation: false\n"
        self.assertIn("duplicate key", self.check()[0])

    def test_repository_maintenance_skills_are_checked(self):
        self.shared_skill()
        self.edit(".agents/skills/example/agents/openai.yaml", "true", "false")
        self.assertIn("opposite", self.check()[0])

    def test_matching_wrapper_needs_no_ui_file(self):
        self.shared_skill()
        self.assertEqual(self.check(), [])

    def test_wrapper_drift_reports_the_rendered_wrapper(self):
        self.shared_skill()
        for text in [WRAPPER.replace("Use when", "Trigger when"),
                     WRAPPER.replace("name: example", "name: example\nmetadata:\n  internal: true"),
                     WRAPPER.replace(".agents/skills/example/", ".agents/skills/missing/"),
                     WRAPPER + "\nExtra workflow instructions.\n",
                     WRAPPER.replace("description: Use", "description:  Use")]:
            with self.subTest(text=text):
                self.files[".claude/skills/example/SKILL.md"] = text
                errors = self.check()
                self.assertEqual(len(errors), 1, errors)
                self.assertIn(".claude/skills/example/SKILL.md: Claude wrapper must match", errors[0])
                self.assertIn(WRAPPER, errors[0])

    def test_shared_skill_requires_claude_wrapper(self):
        self.shared_skill()
        del self.files[".claude/skills/example/SKILL.md"]
        self.assertIn(".claude/skills/example/SKILL.md: Claude wrapper must match", self.check()[0])

    def test_orphaned_wrapper_is_rejected(self):
        self.shared_skill()
        del self.files[".agents/skills/example/SKILL.md"]
        self.assertIn("wrapper is missing its shared skill", self.check()[0])


class Hook(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.skill = self.root / "skills/example/SKILL.md"
        (self.skill.parent / "agents").mkdir(parents=True)
        self.skill.write_text(SKILL, encoding="utf-8")
        (self.skill.parent / "agents/openai.yaml").write_text(UI, encoding="utf-8")
        self.git("init", "-q")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.STDOUT)

    def test_hook_blocks_invalid_commit(self):
        # A real commit exercises interpreter selection and nonzero propagation.
        tools = self.root / "tools"
        tools.mkdir()
        for module in Path(checker.__file__).parent.glob("*.py"):
            if not module.name.startswith("test_"):
                (tools / module.name).write_bytes(module.read_bytes())
        test = tools / "test_gate.py"
        test.write_text("import unittest\n\nclass Gate(unittest.TestCase):\n"
                        "    def test_gate(self):\n        self.fail('test gate failed')\n")
        hook = self.root / ".githooks/pre-commit"
        hook.parent.mkdir()
        hook.write_bytes((Path(__file__).resolve().parents[1] / ".githooks/pre-commit").read_bytes())
        hook.chmod(0o755)
        self.git("config", "core.hooksPath", ".githooks")
        self.git("config", "user.name", "Metadata Test")
        self.git("config", "user.email", "test@example.invalid")
        self.skill.write_text(SKILL.replace("name: example", "name: wrong-name"))
        self.git("add", ".")
        with self.assertRaises(subprocess.CalledProcessError) as failed:
            self.git("commit", "-qm", "Should be blocked")
        self.assertIn(b"name must match", failed.exception.output)
        self.skill.write_text(SKILL)
        self.git("add", ".")
        with self.assertRaises(subprocess.CalledProcessError) as failed:
            self.git("commit", "-qm", "Should fail tests")
        self.assertIn(b"test gate failed", failed.exception.output)
        test.write_text(test.read_text().replace("self.fail('test gate failed')", "self.assertTrue(True)"))
        self.git("add", ".")
        self.git("commit", "-qm", "Valid metadata")

        # Unstaged tooling edits do not trigger tests for a skill-only commit.
        test.write_text(test.read_text().replace("self.assertTrue(True)", "self.fail('test gate failed')"))
        self.skill.write_text(SKILL.replace("Example instructions.", "Updated example instructions."))
        self.git("add", "skills/example/SKILL.md")
        output = self.git("commit", "-qm", "Skill-only change")
        self.assertIn(b"Python tests skipped", output)
        self.git("add", "tools/test_gate.py")
        with self.assertRaises(subprocess.CalledProcessError) as failed:
            self.git("commit", "-qm", "Staged failing test")
        self.assertIn(b"test gate failed", failed.exception.output)

    def test_staged_mode_checks_the_index_not_working_files(self):
        script = Path(checker.__file__)
        run = lambda *args: subprocess.run([sys.executable, str(script), *args], cwd=self.root,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.skill.write_text(SKILL.replace("name: example", "name: wrong-name"))
        self.git("add", ".")
        self.skill.write_text(SKILL)
        self.assertEqual(run().returncode, 0)
        staged = run("--staged")
        self.assertEqual(staged.returncode, 1)
        self.assertIn("name must match", staged.stderr)

    def test_staged_tooling_filter_includes_hook_deletions_and_moves(self):
        tool = self.root / "tools/example.py"
        hook = self.root / ".githooks/pre-commit"
        for path in (tool, hook):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("example\n")
        self.git("add", ".")
        self.assertTrue(checker.staged_tooling_changed(self.root))
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "-c", "core.hooksPath=/dev/null", "commit", "-qm", "Fixture")
        self.assertFalse(checker.staged_tooling_changed(self.root))
        self.git("mv", "tools/example.py", "example.py")
        self.assertTrue(checker.staged_tooling_changed(self.root))
        self.git("mv", "example.py", "tools/example.py")
        self.assertFalse(checker.staged_tooling_changed(self.root))
        hook.unlink()
        self.git("add", "-u")
        self.assertTrue(checker.staged_tooling_changed(self.root))


if __name__ == "__main__":
    unittest.main()
