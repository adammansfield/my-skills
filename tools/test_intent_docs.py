"""Exercise the intent-doc contract through its parse interface."""

import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location("intent_docs", Path(__file__).with_name("intent_docs.py"))
intent_docs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(intent_docs)

BASELINE = "a" * 40
DOC = '''# Example

An example skill.

## Invocation

Use the example trigger.
'''
UPSTREAM = '''
## Upstream

### Sources

[example](https://github.com/mattpocock/skills/blob/main/skills/example/SKILL.md).

### Desired differences

Free-form notes.

### Diff

Compared with [upstream commit](https://github.com/mattpocock/skills/commit/{}).

````diff
+ https://github.com/mattpocock/skills/commit/{}
````
'''.format(BASELINE, "b" * 40)


class Parse(unittest.TestCase):
    def test_original_doc_has_no_upstream(self):
        self.assertIsNone(intent_docs.parse(DOC).upstream)

    def test_upstream_doc_exposes_source_and_baseline(self):
        upstream = intent_docs.parse(DOC + UPSTREAM).upstream
        self.assertEqual(upstream.source, "skills/example")
        self.assertEqual(upstream.baseline, BASELINE)

    def test_invocation_body_is_exposed(self):
        self.assertEqual(intent_docs.parse(DOC).body("Invocation").strip(), "Use the example trigger.")

    def test_contract_violations(self):
        for text, message in [
            (DOC.replace("# Example", "## Example"), "# Skill Name"),
            (DOC + "\n# Second title\n", "# Skill Name"),
            ("Preamble.\n\n" + DOC, "# Skill Name"),
            (DOC.replace("An example skill.", ""), "description"),
            (DOC.replace("## Invocation", "## Usage"), "## Invocation"),
            (DOC + "\n## Invocation\n", "## Invocation"),
            (DOC + UPSTREAM.replace("## Upstream\n", ""), "require ## Upstream"),
            (DOC + "\n## Upstream\n\nNo subsections.\n", "### subsections"),
            (DOC + UPSTREAM.replace("### Sources", "#### Sources"), "### subsections"),
            (DOC + UPSTREAM + "\n## Upstream\n", "exactly one ## Upstream"),
            (DOC + "\n## Upstream\n\n## Other\n\n### Sources\n", "### subsections"),
            (DOC + "\n## Upstream\n\n### Notes\n\nUntracked.\n", "### Sources"),
            (DOC + UPSTREAM.replace("### Diff", "### Snapshot"), "### Diff"),
            (DOC + UPSTREAM.replace("blob/main/skills/example", "tree/main/skills/example"), "unambiguous"),
            (DOC + UPSTREAM.replace("### Desired differences",
                                    "[b](https://github.com/mattpocock/skills/blob/main/b/SKILL.md)\n\n### Desired differences"),
             "unambiguous"),
            (DOC + UPSTREAM.replace("blob/main/skills/example", "blob/main/../example"), "invalid upstream source path"),
            (DOC + UPSTREAM.replace(BASELINE, "a" * 12), "baseline SHA"),
        ]:
            with self.subTest(message=message, text=text):
                with self.assertRaises(ValueError) as raised:
                    intent_docs.parse(text)
                self.assertIn(message, str(raised.exception))

    def test_fenced_examples_are_not_headings(self):
        for fence in ["```", "~~~~"]:
            with self.subTest(fence=fence):
                hidden = DOC.replace("## Invocation", fence + "\n## Invocation\n" + fence)
                with self.assertRaises(ValueError):
                    intent_docs.parse(hidden)
                fake = DOC + "\n" + fence + "diff\n# Fake title\n## Upstream\n" + fence + "\n"
                self.assertIsNone(intent_docs.parse(fake).upstream)


class DeclaresUpstream(unittest.TestCase):
    def test_detects_the_heading_without_validating_the_doc(self):
        self.assertTrue(intent_docs.declares_upstream("## Upstream\n"))
        self.assertTrue(intent_docs.declares_upstream(DOC + UPSTREAM))
        self.assertFalse(intent_docs.declares_upstream(DOC))
        self.assertFalse(intent_docs.declares_upstream("```\n## Upstream\n```\n"))


class WithDiff(unittest.TestCase):
    def test_replaces_only_the_diff_section(self):
        target = "c" * 40
        text = DOC + UPSTREAM + "\n## Other\n\nKeep this.\n"
        updated = intent_docs.with_diff(intent_docs.parse(text), target, [("SKILL.md", "-old\n+```\n")])
        self.assertEqual(intent_docs.parse(updated).upstream.baseline, target)
        self.assertEqual(updated.split("### Diff")[0], text.split("### Diff")[0])
        self.assertTrue(updated.endswith("\n## Other\n\nKeep this.\n"))
        self.assertIn("#### SKILL.md\n\n````diff\n-old\n+```\n````\n", updated)

    def test_keeps_crlf_line_endings(self):
        text = (DOC + UPSTREAM).replace("\n", "\r\n")
        updated = intent_docs.with_diff(intent_docs.parse(text), "c" * 40, [("SKILL.md", "+new\n")])
        self.assertNotIn("\n", updated.replace("\r\n", ""))


if __name__ == "__main__":
    unittest.main()
