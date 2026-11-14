"""Exercise snapshot generation, safe writes, and checkout-local freshness state."""

from datetime import datetime, timedelta, timezone
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


class UpstreamSnapshots(unittest.TestCase):
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
        self.source = "skills/productivity/example"
        self.skill = self.upstream / self.source / "SKILL.md"
        self.skill.parent.mkdir(parents=True)
        self.skill.write_text("Original workflow.\n\n### Diff\n\n````example\nKeep this fence.\n````\n")
        ui = self.skill.parent / "agents/openai.yaml"
        ui.parent.mkdir()
        ui.write_text('interface:\n  display_name: "Example"\n')
        self.baseline = self.commit("Original skill")
        self.skill.write_text(self.skill.read_text() + "\nNew upstream behavior.\n")
        self.target = self.commit("Improve upstream skill")
        self.doc = self.add_adaptation("widget")
        self.now = datetime(2026, 11, 10, tzinfo=timezone.utc)
        self.tree = snapshots.repo.WorkingTree(self.root)

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
        doc.write_text('''# Local skill

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

[example](https://github.com/mattpocock/skills/blob/main/skills/productivity/example/SKILL.md).

### Desired differences

Preserve this exact requirement.

### Diff

[baseline](https://github.com/mattpocock/skills/commit/BASELINE)

````diff
Old snapshot.
````

### Additional notes

Preserve these notes too.

## Other

Keep this final section.
'''.replace("BASELINE", self.baseline))
        return doc

    def add_in_repo_adaptation(self, name, source):
        doc = self.add_adaptation(name)
        text = doc.read_text()
        start, end = text.rindex("### Sources"), text.index("### Desired differences")
        doc.write_text(text[:start] + "### Sources\n\n[{0}](../../skills/{0}/SKILL.md).\n\n".format(source)
                       + text[end:].replace("[baseline](https://github.com/mattpocock/skills/commit/{})".format(self.baseline),
                                            "Compared with the working tree."))
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

    def test_write_preserves_requirements_and_suffix_bytes_including_crlf(self):
        self.doc.write_bytes(self.doc.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        before = self.doc.read_bytes()
        self.assertEqual(self.snapshot_cli("--write").returncode, 0)
        after = self.doc.read_bytes()
        self.assertEqual(before.split(b"### Diff\r\n", 1)[0], after.split(b"### Diff\r\n", 1)[0])
        self.assertEqual(before.split(b"### Additional notes", 1)[1], after.split(b"### Additional notes", 1)[1])
        self.assertNotIn(b"\n", after.replace(b"\r\n", b""))

    def test_nested_fences_and_headings_do_not_confuse_section_boundaries(self):
        self.assertEqual(self.snapshot_cli("--write").returncode, 0)
        self.assertIn("`````diff", self.doc.read_text())
        self.assertEqual(self.snapshot_cli().returncode, 0)

    def test_commit_links_in_patch_content_are_not_snapshot_baselines(self):
        self.skill.write_text(self.skill.read_text() + "\nSee https://github.com/mattpocock/skills/commit/" + "b" * 40 + "\n")
        self.target = self.commit("Add a source reference")
        written = self.snapshot_cli("--write")
        self.assertEqual(written.returncode, 0, written.stderr)
        checked = self.snapshot_cli()
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_selection_changes_only_requested_skill(self):
        other = self.add_adaptation("another")
        original = other.read_bytes()
        self.assertEqual(self.snapshot_cli("--skill", "widget", "--write").returncode, 0)
        self.assertEqual(other.read_bytes(), original)
        missing = self.snapshot_cli("--skill", "unknown")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("unknown", missing.stderr)

    def test_snapshots_compare_only_the_named_upstream(self):
        other = self.add_adaptation("other-upstream")
        other.write_text(other.read_text().replace(MATT, OTHER))
        original = other.read_bytes()
        result = self.snapshot_cli("--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([s["skill"] for s in json.loads(result.stdout)["skills"]], ["widget"])
        self.assertEqual(other.read_bytes(), original)
        mismatched = self.snapshot_cli("--skill", "other-upstream")
        self.assertEqual(mismatched.returncode, 2)
        self.assertIn("other-upstream", mismatched.stderr)

    def test_snapshot_mode_requires_an_upstream(self):
        result = self.cli("--upstream-dir", str(self.upstream), "--ref", "HEAD")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--upstream", result.stderr)

    def test_in_repo_snapshots_compare_with_the_working_tree_source(self):
        doc = self.add_in_repo_adaptation("variant", "widget")
        (self.root / "skills/variant/SKILL.md").write_text("Variant workflow.\n")
        checked = self.cli("--in-repo")
        self.assertEqual(checked.returncode, 1, checked.stderr)
        self.assertEqual([s["skill"] for s in json.loads(checked.stdout)["skills"]], ["variant"])
        self.assertEqual(self.cli("--in-repo", "--write").returncode, 0)
        self.assertIn("-Local workflow.\n+Variant workflow.\n", doc.read_text())
        self.assertIn("Compared with the working-tree [`widget`](../../skills/widget/SKILL.md) files.", doc.read_text())
        self.assertEqual(self.cli("--in-repo").returncode, 0)
        (self.root / "skills/widget/SKILL.md").write_text("Edited source.\n")
        self.assertEqual(self.cli("--in-repo").returncode, 1)

    def test_in_repo_snapshots_skip_external_upstreams(self):
        self.add_in_repo_adaptation("variant", "widget")
        original = self.doc.read_bytes()
        self.assertEqual(self.cli("--in-repo", "--write").returncode, 0)
        self.assertEqual(self.doc.read_bytes(), original)
        self.assertEqual(self.cli("--in-repo", "--skill", "widget").returncode, 2)

    def test_in_repo_cycles_and_missing_sources_are_errors(self):
        for docs in [[("loop", "loop")], [("one", "two"), ("two", "one")], [("orphan", "missing")]]:
            with self.subTest(docs=docs):
                paths = [self.add_in_repo_adaptation(name, source) for name, source in docs]
                originals = [p.read_bytes() for p in paths]
                result = self.cli("--in-repo", "--write")
                self.assertEqual(result.returncode, 2)
                self.assertIn(docs[0][0], result.stderr)
                self.assertEqual([p.read_bytes() for p in paths], originals)
                for path in paths:
                    path.unlink()

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

    def test_unrelated_commit_is_not_reported_as_source_change(self):
        (self.upstream / "unrelated.txt").write_text("New work elsewhere.\n")
        self.target = self.commit("Unrelated work")
        self.doc.write_text(self.doc.read_text().replace(self.baseline, self.git(self.upstream, "rev-parse", "HEAD~1")))
        result = self.snapshot_cli()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["skills"][0]["source_changed"])

    def test_reads_committed_sources_not_upstream_worktree(self):
        self.assertEqual(self.snapshot_cli("--write").returncode, 0)
        self.skill.write_text("Uncommitted upstream edits.\n")
        self.assertEqual(self.snapshot_cli().returncode, 0)

    def test_patch_records_missing_final_newline(self):
        delta = snapshots.patch("before", "after", "source", "local")
        self.assertIn("-before\n\\ No newline at end of file\n", delta)
        self.assertIn("+after\n\\ No newline at end of file\n", delta)

    def test_original_skills_without_upstream_are_skipped(self):
        (self.doc.parent / "original.md").write_text("# Original\n\nA workflow.\n\n## Invocation\n\nExplicit.\n")
        self.assertEqual(len(snapshots.adaptations(self.tree)), 1)

    def test_status_without_record_is_due_and_does_not_write(self):
        self.assertTrue(snapshots.freshness(self.tree, self.now)["due"])
        self.assertFalse(snapshots.state_path(self.tree).exists())
        result = self.cli("--status")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)["due"])
        self.assertEqual(json.loads(result.stdout)["skills"], ["widget"])

    def test_freshness_boundary_and_local_untracked_state(self):
        snapshots.record_check(self.tree, MATT, self.target, self.now)
        self.assertFalse(snapshots.freshness(self.tree, self.now + timedelta(days=29))["due"])
        self.assertEqual(snapshots.freshness(self.tree, self.now)["skills"], ["widget"])
        self.assertTrue(snapshots.freshness(self.tree, self.now + timedelta(days=30))["due"])
        self.assertNotIn("upstream-check.json", self.git(self.root, "ls-files", "--others", "--exclude-standard"))

    def test_new_document_baseline_invalidates_fresh_record(self):
        snapshots.record_check(self.tree, MATT, self.target, self.now)
        self.doc.write_text(self.doc.read_text().replace(self.baseline, self.target))
        self.assertTrue(snapshots.freshness(self.tree, self.now)["due"])

    def test_corrupt_or_future_record_is_due(self):
        snapshots.record_check(self.tree, MATT, self.target, self.now + timedelta(days=1))
        self.assertTrue(snapshots.freshness(self.tree, self.now)["due"])
        snapshots.state_path(self.tree).write_text("not json")
        self.assertTrue(snapshots.freshness(self.tree, self.now)["due"])

    def test_malformed_doc_is_an_error_not_a_due_check(self):
        snapshots.record_check(self.tree, MATT, self.target, self.now)
        self.doc.write_text(self.doc.read_text().replace("### Sources", "### Notes"))
        with self.assertRaises(ValueError):
            snapshots.freshness(self.tree, self.now)
        result = self.cli("--status")
        self.assertEqual(result.returncode, 2)
        self.assertIn("widget.md", result.stderr)

    def test_broken_doc_without_upstream_does_not_affect_status(self):
        (self.doc.parent / "draft.md").write_text("# Draft\n\nA skill in progress.\n")
        result = self.cli("--status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["skills"], ["widget"])

    def test_repository_without_external_upstreams_is_never_due(self):
        self.doc.unlink()
        self.assertFalse(snapshots.freshness(self.tree, self.now)["due"])
        with self.assertRaises(ValueError):
            snapshots.record_check(self.tree, MATT, self.target, self.now)

    def test_each_upstream_has_its_own_record(self):
        other = self.add_adaptation("other-upstream")
        other.write_text(other.read_text().replace(MATT, OTHER))
        snapshots.record_check(self.tree, MATT, self.target, self.now)
        status = snapshots.freshness(self.tree, self.now)
        self.assertTrue(status["due"])
        by_url = {u["url"]: u for u in status["upstreams"]}
        self.assertFalse(by_url[MATT]["due"])
        self.assertEqual(by_url[MATT]["skills"], ["widget"])
        self.assertTrue(by_url[OTHER]["due"])
        snapshots.record_check(self.tree, OTHER, self.target, self.now)
        self.assertFalse(snapshots.freshness(self.tree, self.now)["due"])

    def test_in_repo_adaptations_are_listed_but_never_due(self):
        self.add_in_repo_adaptation("variant", "widget")
        snapshots.record_check(self.tree, MATT, self.target, self.now)
        status = snapshots.freshness(self.tree, self.now)
        self.assertFalse(status["due"])
        self.assertEqual(status["in_repo"], ["variant"])
        self.assertEqual(status["skills"], ["variant", "widget"])

    def test_single_upstream_record_format_is_due(self):
        snapshots.state_path(self.tree).write_text(json.dumps(dict(
            checked_at=self.now.isoformat(), upstream_sha=self.target, scope="x")))
        self.assertTrue(snapshots.freshness(self.tree, self.now)["due"])

    def test_record_requires_full_scope_and_valid_sha(self):
        self.assertEqual(self.cli("--record-check", self.target, "--upstream", MATT, "--skill", "widget").returncode, 2)
        self.assertEqual(self.cli("--record-check", "short-sha", "--upstream", MATT).returncode, 2)
        self.assertEqual(self.cli("--record-check", self.target).returncode, 2)
        self.assertFalse(snapshots.state_path(self.tree).exists())
        self.assertEqual(self.cli("--record-check", self.target, "--upstream", MATT).returncode, 0)
        self.assertFalse(json.loads(self.cli("--status").stdout)["due"])

if __name__ == "__main__":
    unittest.main()
