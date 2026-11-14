"""Exercise the skill catalog through in-memory trees."""

import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location("catalog", Path(__file__).with_name("catalog.py"))
catalog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(catalog)
from repo import MemoryTree  # noqa: E402  (tools/ is on the path, as catalog's own imports need)


SKILL = "---\r\nname: example\r\ndescription: 'It''s an example' # comment\r\n---\r\n\r\nBody.\r\n"
UI = 'interface:\n  display_name: "Example"\n'


class Catalog(unittest.TestCase):
    def test_reads_each_kind_of_skill_and_doc(self):
        found = catalog.read(MemoryTree({
            "skills/example/SKILL.md": SKILL, "skills/example/agents/openai.yaml": UI,
            ".agents/skills/tool/SKILL.md": SKILL, ".agents/skills/tool/agents/openai.yaml": UI,
            ".claude/skills/tool/SKILL.md": "wrapper", "docs/skills/example.md": "# Example\n\nA skill.\n",
            "docs/skills/notes/extra.md": "ignored"}))
        skill = found.skills["example"]
        self.assertEqual(skill.fields[("description",)], "It's an example")
        self.assertEqual(skill.frontmatter, SKILL[:SKILL.index("\r\n\r\n") + 2])
        self.assertEqual(skill.ui[("interface", "display_name")], "Example")
        self.assertEqual(list(found.internal), ["tool"])
        self.assertEqual(found.wrappers["tool"].text, "wrapper")
        self.assertEqual(list(found.docs), ["example"])
        self.assertIsNone(found.docs["example"].doc)
        self.assertFalse(found.docs["example"].adapted)
        self.assertEqual([path for path, _ in found.problems], ["docs/skills/example.md"])

    def test_bad_files_become_problems_on_their_own_paths(self):
        found = catalog.read(MemoryTree({
            "skills/example/SKILL.md": "no frontmatter", "skills/example/agents/openai.yaml": "key: [list]\n",
            "skills/other/SKILL.md": SKILL, "skills/nested/deeper/SKILL.md": SKILL}))
        self.assertEqual(found.problems, [
            ("skills/nested/deeper/SKILL.md", "skills must be at skills/NAME/SKILL.md"),
            ("skills/example/SKILL.md", "missing YAML frontmatter delimiters"),
            ("skills/example/agents/openai.yaml", "use a single-line plain or quoted scalar"),
            ("skills/other/SKILL.md", "missing skills/other/agents/openai.yaml")])
        self.assertIsNone(found.skills["example"].fields)
        self.assertIsNone(found.skills["example"].ui)
        self.assertEqual(found.skills["other"].fields[("name",)], "example")

    def test_yaml_subset_rejects_duplicates_and_bad_indentation(self):
        for text, message in [("a: 1\na: 2\n", "duplicate key a"), ("a:\n   b: 1\n", "expected 2 spaces")]:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, message):
                catalog.mapping(text)


if __name__ == "__main__":
    unittest.main()
