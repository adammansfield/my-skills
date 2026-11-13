"""Exercise the metadata guardrail and its staged-file behavior using only stdlib."""

import importlib.util
from pathlib import Path
import subprocess
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


class MetadataChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.skill = self.root / "skills/example/SKILL.md"
        self.ui = self.skill.parent / "agents/openai.yaml"
        self.ui.parent.mkdir(parents=True)
        self.skill.write_text(SKILL, encoding="utf-8")
        self.ui.write_text(UI, encoding="utf-8")
        self.git("init", "-q")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.STDOUT)

    def shared_skill(self):
        source = self.root / ".agents/skills/example/SKILL.md"
        wrapper = self.root / ".claude/skills/example/SKILL.md"
        ui = source.parent / "agents/openai.yaml"
        ui.parent.mkdir(parents=True)
        wrapper.parent.mkdir(parents=True)
        source.write_text(SKILL, encoding="utf-8")
        ui.write_text(UI, encoding="utf-8")
        header = SKILL[:SKILL.index("\n---", 3) + 4]
        wrapper.write_text(header + "\n\nRead and follow `.agents/skills/example/SKILL.md` from this repository's root.\n", encoding="utf-8")
        return source, wrapper

    def test_valid_model_callable_skill(self):
        self.assertEqual(checker.check(self.root), [])

    def add_doc(self, text=DOC):
        doc = self.root / "docs/skills/example.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(text, encoding="utf-8")
        return doc

    def test_original_and_upstream_docs_are_valid(self):
        for text in [DOC, DOC + UPSTREAM]:
            with self.subTest(text=text):
                self.add_doc(text)
                self.assertEqual(checker.check(self.root), [])

    def test_doc_contract_errors_name_the_doc(self):
        # The full contract is covered by test_intent_docs; this checks the checker reports it.
        self.add_doc(DOC + "\n## Upstream\n\n### Notes\n\nUntracked.\n")
        errors = checker.check(self.root)
        self.assertIn("docs/skills/example.md:", errors[0])
        self.assertIn("### Sources", errors[0])

    def test_docs_use_staged_content(self):
        doc = self.add_doc(DOC.replace("## Invocation", "## Usage"))
        self.git("add", ".")
        doc.write_text(DOC)
        self.assertEqual(checker.check(self.root), [])
        self.assertIn("## Invocation", checker.check(self.root, staged=True)[0])
        self.git("add", ".")
        doc.write_text(DOC.replace("## Invocation", "## Usage"))
        self.assertIn("## Invocation", checker.check(self.root)[0])
        self.assertEqual(checker.check(self.root, staged=True), [])
        doc.unlink()
        self.git("add", "-u")
        self.assertEqual(checker.check(self.root, staged=True), [])

    def test_explicit_only_requires_matching_host_policies(self):
        self.skill.write_text(SKILL.replace("name: example", "name: example\ndisable-model-invocation: true"))
        self.assertIn("opposite", checker.check(self.root)[0])
        self.ui.write_text(UI.replace("true", "false"))
        self.assertEqual(checker.check(self.root), [])

    def test_name_must_match_directory(self):
        self.skill.write_text(SKILL.replace("name: example", "name: wrong-name"))
        self.assertIn("name must match", checker.check(self.root)[0])

    def test_quoted_boolean_is_not_boolean(self):
        self.ui.write_text(UI.replace("true", '"true"'))
        self.assertIn("opposite", checker.check(self.root)[0])

    def test_missing_ui_is_reported(self):
        self.ui.unlink()
        self.assertTrue(checker.check(self.root))

    def test_short_description_length_is_checked(self):
        self.ui.write_text(UI.replace("An example skill for metadata validation", "Too short"))
        self.assertIn("25–64", checker.check(self.root)[0])

    def test_duplicate_metadata_is_rejected(self):
        self.ui.write_text(UI + "policy:\n  allow_implicit_invocation: false\n")
        self.assertIn("duplicate key", checker.check(self.root)[0])

    def test_staged_invalid_version_cannot_be_hidden_by_working_fix(self):
        self.skill.write_text(SKILL.replace("name: example", "name: wrong-name"))
        self.git("add", ".")
        self.skill.write_text(SKILL)
        self.assertEqual(checker.check(self.root), [])
        self.assertIn("name must match", checker.check(self.root, staged=True)[0])

    def test_unstaged_error_does_not_block_valid_staged_version(self):
        self.git("add", ".")
        self.ui.write_text(UI.replace("true", "false"))
        self.assertTrue(checker.check(self.root))
        self.assertEqual(checker.check(self.root, staged=True), [])

    def test_repository_maintenance_skills_are_checked(self):
        source, _ = self.shared_skill()
        (source.parent / "agents/openai.yaml").write_text(UI.replace("true", "false"))
        self.assertIn("opposite", checker.check(self.root)[0])

    def test_matching_wrapper_needs_no_ui_file(self):
        self.shared_skill()
        self.assertEqual(checker.check(self.root), [])

    def test_wrapper_metadata_drift_is_rejected(self):
        _, wrapper = self.shared_skill()
        original = wrapper.read_text()
        for old, new in [("Use when", "Trigger when"),
                         ("name: example", "name: example\ndisable-model-invocation: true"),
                         ("name: example", "name: example\nmetadata:\n  internal: true")]:
            with self.subTest(change=new):
                wrapper.write_text(original.replace(old, new))
                self.assertIn("wrapper metadata must match", checker.check(self.root)[0])

    def test_wrapper_must_only_point_to_shared_source(self):
        _, wrapper = self.shared_skill()
        original = wrapper.read_text()
        for text in [original.replace(".agents/skills/example/", ".agents/skills/missing/"),
                     original + "\nExtra workflow instructions.\n"]:
            with self.subTest(text=text):
                wrapper.write_text(text)
                self.assertIn("wrapper body must contain only", checker.check(self.root)[0])

    def test_orphaned_wrapper_is_rejected(self):
        source, _ = self.shared_skill()
        source.unlink()
        self.assertIn("wrapper is missing its shared source", checker.check(self.root)[0])

    def test_shared_skill_requires_claude_wrapper(self):
        _, wrapper = self.shared_skill()
        wrapper.unlink()
        self.assertIn("shared skill is missing its Claude wrapper", checker.check(self.root)[0])

    def test_staged_wrapper_drift_is_not_hidden_by_unstaged_fix(self):
        _, wrapper = self.shared_skill()
        original = wrapper.read_text()
        wrapper.write_text(original.replace("Use when", "Trigger when"))
        self.git("add", ".")
        wrapper.write_text(original)
        self.assertEqual(checker.check(self.root), [])
        self.assertIn("wrapper metadata must match", checker.check(self.root, staged=True)[0])

    def test_unstaged_source_drift_does_not_affect_staged_pair(self):
        source, _ = self.shared_skill()
        self.git("add", ".")
        source.write_text(SKILL.replace("Use when", "Trigger when"))
        self.assertIn("wrapper metadata must match", checker.check(self.root)[0])
        self.assertEqual(checker.check(self.root, staged=True), [])

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
