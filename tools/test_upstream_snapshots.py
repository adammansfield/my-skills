"""Exercise Diff snapshots through in-memory trees, and the CLI and Check record against real Git."""

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("upstream_snapshots", Path(__file__).with_name("upstream_snapshots.py"))
snapshots = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshots)


MATT = "https://github.com/mattpocock/skills"
OTHER = "https://github.com/example-org/agent-skills"
BASE, TARGET = "1" * 40, "2" * 40
SOURCE = "skills/productivity/example"
UPSTREAM_SKILL = "Original workflow.\n\n### Diff\n\n````example\nKeep this fence.\n````\n"
UPSTREAM_UI = 'interface:\n  display_name: "Example"\n'


def adaptation_doc(baseline, repo=MATT):
    return '''# Local skill

A local workflow.

## Invocation

Model-callable.

~~~~example
## Upstream
### Sources
Ignore this fenced example.
~~~~

## Upstream

### Sources

[example](REPO/blob/main/skills/productivity/example/SKILL.md).

### Desired differences

Preserve this exact requirement.

### Diff

[baseline](REPO/commit/BASELINE)

````diff
Old snapshot.
````

### Additional notes

Preserve these notes too.

## Other

Keep this final section.
'''.replace("BASELINE", baseline).replace("REPO", repo)


def in_repo_doc(source):
    text = adaptation_doc(BASE)
    start, end = text.rindex("### Sources"), text.index("### Desired differences")
    return (text[:start] + "### Sources\n\n[{0}](../../skills/{0}/SKILL.md).\n\n".format(source)
            + text[end:].replace("[baseline]({}/commit/{})".format(MATT, BASE), "Compared with the working tree."))


class Snapshots(unittest.TestCase):
    """Diff snapshots compared through in-memory trees."""

    def setUp(self):
        self.files = {}
        self.add_skill("widget", adaptation_doc(BASE))
        self.commits = {BASE: self.upstream(UPSTREAM_SKILL),
                        TARGET: self.upstream(UPSTREAM_SKILL + "\nNew upstream behavior.\n")}

    def add_skill(self, name, doc):
        self.files.update({"skills/{}/SKILL.md".format(name): "Local workflow.\n",
                           "skills/{}/agents/openai.yaml".format(name): 'interface:\n  display_name: "Local"\n',
                           "docs/skills/{}.md".format(name): doc})

    @staticmethod
    def upstream(skill, ui=UPSTREAM_UI):
        files = {SOURCE + "/SKILL.md": skill}
        if ui is not None:
            files[SOURCE + "/agents/openai.yaml"] = ui
        return snapshots.repo.MemoryTree(files)

    def at(self, commit):
        if commit not in self.commits:
            raise ValueError("unknown commit " + commit)
        return self.commits[commit]

    def prepare(self, names=None, url=MATT, target=TARGET):
        return snapshots.prepare(snapshots.repo.MemoryTree(self.files), url, target, self.at, names)

    def prepare_in_repo(self, names=None):
        return snapshots.prepare_in_repo(snapshots.repo.MemoryTree(self.files), names)

    def apply(self, pending):
        self.files.update(pending)

    def test_stale_snapshot_is_rebuilt_and_then_current(self):
        pending, report = self.prepare()
        self.assertEqual(report, [dict(skill="widget", baseline=BASE, source_changed=True, snapshot_stale=True)])
        updated = dict(pending)["docs/skills/widget.md"]
        self.assertIn("Compared with [upstream commit `{}`]({}/commit/{}).".format(TARGET[:12], MATT, TARGET), updated)
        self.assertIn("+Local workflow.\n", updated)
        self.apply(pending)
        self.assertEqual(self.prepare()[0], [])

    def test_rebuild_preserves_requirements_and_suffix_including_crlf(self):
        doc = "docs/skills/widget.md"
        self.files[doc] = self.files[doc].replace("\n", "\r\n")
        before = self.files[doc]
        after = dict(self.prepare()[0])[doc]
        self.assertEqual(before.split("### Diff\r\n", 1)[0], after.split("### Diff\r\n", 1)[0])
        self.assertEqual(before.split("### Additional notes", 1)[1], after.split("### Additional notes", 1)[1])
        self.assertNotIn("\n", after.replace("\r\n", ""))

    def test_nested_fences_and_headings_do_not_confuse_section_boundaries(self):
        self.apply(self.prepare()[0])
        self.assertIn("`````diff", self.files["docs/skills/widget.md"])
        self.assertEqual(self.prepare()[0], [])

    def test_commit_links_in_patch_content_are_not_snapshot_baselines(self):
        link = "\nSee {}/commit/{}\n".format(MATT, "b" * 40)
        self.commits[TARGET] = self.upstream(UPSTREAM_SKILL + link)
        self.apply(self.prepare()[0])
        self.assertEqual(self.prepare()[0], [])

    def test_unrelated_commit_is_not_reported_as_source_change(self):
        self.commits[TARGET] = self.commits[BASE]
        pending, report = self.prepare()
        self.assertTrue(pending)
        self.assertFalse(report[0]["source_changed"])

    def test_selection_compares_only_requested_skills(self):
        self.add_skill("another", adaptation_doc(BASE))
        pending, report = self.prepare(["widget"])
        self.assertEqual([path for path, _ in pending], ["docs/skills/widget.md"])
        self.assertEqual([r["skill"] for r in report], ["widget"])
        with self.assertRaisesRegex(ValueError, "unknown"):
            self.prepare(["unknown"])

    def test_snapshots_compare_only_the_named_upstream(self):
        self.add_skill("other-upstream", adaptation_doc(BASE, OTHER))
        self.assertEqual([r["skill"] for r in self.prepare()[1]], ["widget"])
        with self.assertRaisesRegex(ValueError, "other-upstream"):
            self.prepare(["other-upstream"])
        with self.assertRaisesRegex(ValueError, "no skills are adapted"):
            self.prepare(url="https://github.com/example-org/unused")

    def test_ambiguous_mapping_names_the_doc(self):
        doc = "docs/skills/widget.md"
        self.files[doc] = self.files[doc].replace("### Desired differences", "[duplicate]({}/blob/main/x/SKILL.md)\n\n"
                                                  "### Desired differences".format(MATT))
        with self.assertRaisesRegex(ValueError, "widget.md: .*unambiguous"):
            self.prepare()

    def test_missing_upstream_file_names_the_doc_and_file(self):
        self.commits[TARGET] = self.upstream(UPSTREAM_SKILL, ui=None)
        with self.assertRaisesRegex(ValueError, "widget.md: .*agents/openai.yaml"):
            self.prepare()

    def test_missing_local_file_names_the_doc_and_file(self):
        del self.files["skills/widget/agents/openai.yaml"]
        with self.assertRaisesRegex(ValueError, "widget.md: .*skills/widget/agents/openai.yaml"):
            self.prepare()

    def test_missing_baseline_fails(self):
        self.files["docs/skills/widget.md"] = adaptation_doc("a" * 40)
        with self.assertRaisesRegex(ValueError, "a" * 40):
            self.prepare()

    def test_in_repo_snapshots_compare_with_the_source_in_the_same_tree(self):
        self.add_skill("variant", in_repo_doc("widget"))
        self.files["skills/variant/SKILL.md"] = "Variant workflow.\n"
        pending, report = self.prepare_in_repo()
        self.assertEqual(report, [dict(skill="variant", source="skills/widget", snapshot_stale=True)])
        updated = dict(pending)["docs/skills/variant.md"]
        self.assertIn("-Local workflow.\n+Variant workflow.\n", updated)
        self.assertIn("Compared with the working-tree [`widget`](../../skills/widget/SKILL.md) files.", updated)
        self.apply(pending)
        self.assertEqual(self.prepare_in_repo()[0], [])
        self.files["skills/widget/SKILL.md"] = "Edited source.\n"
        self.assertEqual(len(self.prepare_in_repo()[0]), 1)

    def test_in_repo_snapshots_skip_external_upstreams(self):
        self.add_skill("variant", in_repo_doc("widget"))
        self.assertEqual([r["skill"] for r in self.prepare_in_repo()[1]], ["variant"])
        with self.assertRaisesRegex(ValueError, "widget"):
            self.prepare_in_repo(["widget"])

    def test_in_repo_cycles_and_missing_sources_are_errors(self):
        for docs in [[("loop", "loop")], [("one", "two"), ("two", "one")], [("orphan", "missing")]]:
            with self.subTest(docs=docs):
                self.setUp()
                for name, source in docs:
                    self.add_skill(name, in_repo_doc(source))
                with self.assertRaisesRegex(ValueError, docs[0][0]):
                    self.prepare_in_repo()

    def test_original_skills_without_upstream_are_skipped(self):
        self.files["docs/skills/original.md"] = "# Original\n\nA workflow.\n\n## Invocation\n\nExplicit.\n"
        self.assertEqual([a.name for a in snapshots.adaptations(snapshots.repo.MemoryTree(self.files))], ["widget"])

    def test_patch_records_missing_final_newline(self):
        delta = snapshots.patch("before", "after", "source", "local")
        self.assertIn("-before\n\\ No newline at end of file\n", delta)
        self.assertIn("+after\n\\ No newline at end of file\n", delta)


class CommandLine(unittest.TestCase):
    """The CLI and checkout-local Check record against real Git repositories."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "local"
        self.upstream = Path(temporary.name) / "upstream"
        for root in (self.root, self.upstream):
            root.mkdir()
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Snapshot Test")
            self.git(root, "config", "user.email", "test@example.invalid")
        self.skill = self.upstream / SOURCE / "SKILL.md"
        self.skill.parent.mkdir(parents=True)
        self.skill.write_text(UPSTREAM_SKILL)
        ui = self.skill.parent / "agents/openai.yaml"
        ui.parent.mkdir()
        ui.write_text(UPSTREAM_UI)
        self.baseline = self.commit("Original skill")
        self.skill.write_text(self.skill.read_text() + "\nNew upstream behavior.\n")
        self.target = self.commit("Improve upstream skill")
        self.doc = self.add_adaptation("widget")
        self.now = datetime(2026, 11, 10, tzinfo=timezone.utc)

    def git(self, root, *args):
        return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.STDOUT).decode().strip()

    def commit(self, message):
        self.git(self.upstream, "add", ".")
        self.git(self.upstream, "commit", "-qm", message)
        return self.git(self.upstream, "rev-parse", "HEAD")

    def add_adaptation(self, name):
        local = self.root / "skills" / name
        (local / "agents").mkdir(parents=True)
        (local / "SKILL.md").write_text("Local workflow.\n")
        (local / "agents/openai.yaml").write_text('interface:\n  display_name: "Local"\n')
        doc = self.root / "docs/skills" / (name + ".md")
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(adaptation_doc(self.baseline))
        return doc

    def add_in_repo_adaptation(self, name, source):
        doc = self.add_adaptation(name)
        doc.write_text(in_repo_doc(source))
        return doc

    def cli(self, *args):
        return subprocess.run([sys.executable, snapshots.__file__, *args], cwd=self.root,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def snapshot_cli(self, *args):
        return self.cli("--upstream", MATT, "--upstream-dir", str(self.upstream), "--ref", "HEAD", *args)

    def test_check_is_read_only_and_write_is_idempotent(self):
        original = self.doc.read_bytes()
        checked = self.snapshot_cli()
        self.assertEqual(checked.returncode, 1, checked.stderr)
        self.assertEqual(self.doc.read_bytes(), original)
        self.assertTrue(json.loads(checked.stdout)["skills"][0]["source_changed"])
        written = self.snapshot_cli("--write")
        self.assertEqual(written.returncode, 0, written.stderr)
        updated = self.doc.read_bytes()
        self.assertIn(self.target.encode(), updated)
        self.assertEqual(self.snapshot_cli().returncode, 0)
        self.assertEqual(self.snapshot_cli("--write").returncode, 0)
        self.assertEqual(self.doc.read_bytes(), updated)

    def test_snapshot_mode_requires_an_upstream(self):
        result = self.cli("--upstream-dir", str(self.upstream), "--ref", "HEAD")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--upstream", result.stderr)

    def test_in_repo_check_reads_the_working_tree_and_write_refreshes(self):
        doc = self.add_in_repo_adaptation("variant", "widget")
        (self.root / "skills/variant/SKILL.md").write_text("Variant workflow.\n")
        checked = self.cli("--in-repo")
        self.assertEqual(checked.returncode, 1, checked.stderr)
        self.assertEqual([s["skill"] for s in json.loads(checked.stdout)["skills"]], ["variant"])
        self.assertEqual(self.cli("--in-repo", "--write").returncode, 0)
        self.assertIn("+Variant workflow.\n", doc.read_text())
        self.assertEqual(self.cli("--in-repo").returncode, 0)

    def test_in_repo_mode_rejects_external_options(self):
        self.assertEqual(self.cli("--in-repo", "--upstream", MATT).returncode, 2)

    def test_ambiguous_mapping_prevents_all_writes(self):
        other = self.add_adaptation("z-other")
        other.write_text(other.read_text().replace("### Desired differences", "[duplicate](https://github.com/mattpocock/skills/blob/main/other/SKILL.md)\n\n### Desired differences"))
        originals = [p.read_bytes() for p in (self.doc, other)]
        result = self.snapshot_cli("--write")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unambiguous", result.stderr)
        self.assertEqual([p.read_bytes() for p in (self.doc, other)], originals)

    def test_missing_blob_is_an_error_without_writes(self):
        (self.skill.parent / "agents/openai.yaml").unlink()
        self.commit("Remove metadata")
        original = self.doc.read_bytes()
        result = self.snapshot_cli("--write")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.doc.read_bytes(), original)

    def test_invalid_ref_or_missing_baseline_fails_clearly(self):
        invalid = self.cli("--upstream", MATT, "--upstream-dir", str(self.upstream), "--ref", "no-such-ref")
        self.assertEqual(invalid.returncode, 2)
        self.doc.write_text(self.doc.read_text().replace(self.baseline, "a" * 40))
        self.assertEqual(self.snapshot_cli().returncode, 2)

    def status(self):
        result = self.cli("--status")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_status_without_record_is_due_and_does_not_write(self):
        status = self.status()
        self.assertTrue(status["due"])
        self.assertEqual(status["skills"], ["widget"])
        self.assertFalse(snapshots.check_record.path(self.root).exists())

    def test_recorded_check_is_checkout_local_and_untracked(self):
        recorded = self.cli("--record-check", self.target, "--upstream", MATT)
        self.assertEqual(recorded.returncode, 0, recorded.stderr)
        self.assertEqual(json.loads(recorded.stdout)["upstream_sha"], self.target)
        self.assertFalse(self.status()["due"])
        state = snapshots.check_record.path(self.root)
        self.assertEqual(state.parent.resolve(), (self.root / ".git").resolve())
        self.assertNotIn("upstream-check.json", self.git(self.root, "ls-files", "--others", "--exclude-standard"))

    def test_unreadable_or_old_format_record_is_due(self):
        state = snapshots.check_record.path(self.root)
        for text in ["not json", json.dumps(dict(checked_at=self.now.isoformat(), upstream_sha=self.target, scope="x"))]:
            with self.subTest(text=text):
                state.write_text(text)
                self.assertTrue(self.status()["due"])

    def test_malformed_doc_is_an_error_not_a_due_check(self):
        self.doc.write_text(self.doc.read_text().replace("### Sources", "### Notes"))
        result = self.cli("--status")
        self.assertEqual(result.returncode, 2)
        self.assertIn("widget.md", result.stderr)

    def test_broken_doc_without_upstream_does_not_affect_status(self):
        (self.doc.parent / "draft.md").write_text("# Draft\n\nA skill in progress.\n")
        self.assertEqual(self.status()["skills"], ["widget"])

    def test_record_requires_full_scope_and_valid_sha(self):
        self.assertEqual(self.cli("--record-check", self.target, "--upstream", MATT, "--skill", "widget").returncode, 2)
        self.assertEqual(self.cli("--record-check", "short-sha", "--upstream", MATT).returncode, 2)
        self.assertEqual(self.cli("--record-check", self.target).returncode, 2)
        self.assertFalse(snapshots.check_record.path(self.root).exists())

if __name__ == "__main__":
    unittest.main()
