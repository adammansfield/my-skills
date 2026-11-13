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

    def cli(self, *args):
        return subprocess.run([sys.executable, snapshots.__file__, *args], cwd=self.root,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def snapshot_cli(self, *args):
        return self.cli("--upstream-dir", str(self.upstream), "--ref", "HEAD", *args)

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
        invalid = self.cli("--upstream-dir", str(self.upstream), "--ref", "no-such-ref")
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
        self.assertEqual(len(snapshots.adaptations(self.root)), 1)

    def test_status_without_record_is_due_and_does_not_write(self):
        self.assertTrue(snapshots.freshness(self.root, self.now)["due"])
        self.assertFalse(snapshots.state_path(self.root).exists())
        result = self.cli("--status")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)["due"])
        self.assertEqual(json.loads(result.stdout)["skills"], ["widget"])

    def test_freshness_boundary_and_local_untracked_state(self):
        snapshots.record_check(self.root, self.target, self.now)
        self.assertFalse(snapshots.freshness(self.root, self.now + timedelta(days=29))["due"])
        self.assertEqual(snapshots.freshness(self.root, self.now)["skills"], ["widget"])
        self.assertTrue(snapshots.freshness(self.root, self.now + timedelta(days=30))["due"])
        self.assertNotIn("upstream-check.json", self.git(self.root, "ls-files", "--others", "--exclude-standard"))

    def test_new_document_baseline_invalidates_fresh_record(self):
        snapshots.record_check(self.root, self.target, self.now)
        self.doc.write_text(self.doc.read_text().replace(self.baseline, self.target))
        self.assertTrue(snapshots.freshness(self.root, self.now)["due"])

    def test_corrupt_or_future_record_is_due(self):
        snapshots.record_check(self.root, self.target, self.now + timedelta(days=1))
        self.assertTrue(snapshots.freshness(self.root, self.now)["due"])
        snapshots.state_path(self.root).write_text("not json")
        self.assertTrue(snapshots.freshness(self.root, self.now)["due"])

    def test_malformed_doc_is_an_error_not_a_due_check(self):
        snapshots.record_check(self.root, self.target, self.now)
        self.doc.write_text(self.doc.read_text().replace("### Sources", "### Notes"))
        with self.assertRaises(ValueError):
            snapshots.freshness(self.root, self.now)
        result = self.cli("--status")
        self.assertEqual(result.returncode, 2)
        self.assertIn("widget.md", result.stderr)

    def test_repository_without_adapted_skills_reports_status(self):
        self.doc.unlink()
        self.assertTrue(snapshots.freshness(self.root, self.now)["due"])
        snapshots.record_check(self.root, self.target, self.now)
        self.assertFalse(snapshots.freshness(self.root, self.now)["due"])

    def test_record_requires_full_scope_and_valid_sha(self):
        self.assertEqual(self.cli("--record-check", self.target, "--skill", "widget").returncode, 2)
        self.assertEqual(self.cli("--record-check", "short-sha").returncode, 2)
        self.assertFalse(snapshots.state_path(self.root).exists())


if __name__ == "__main__":
    unittest.main()
