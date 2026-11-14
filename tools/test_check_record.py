"""Exercise Check record rules in-process, with records as plain dicts."""

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location("check_record", Path(__file__).with_name("check_record.py"))
check_record = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_record)
import catalog  # noqa: E402  (tools/ is on the path, as check_record's own imports need)
from repo import MemoryTree  # noqa: E402


MATT = "https://github.com/mattpocock/skills"
OTHER = "https://github.com/example-org/agent-skills"
SHA = "c" * 40
NOW = datetime(2026, 11, 10, tzinfo=timezone.utc)


def doc(source_link, diff):
    return ("# Skill\n\nA skill.\n\n## Invocation\n\nExplicit.\n\n## Upstream\n\n### Sources\n\n"
            "[source]({})\n\n### Diff\n\n{}\n".format(source_link, diff))


def external(repo=MATT, baseline="a" * 40):
    return doc(repo + "/blob/main/skills/example/SKILL.md", "[baseline]({}/commit/{})".format(repo, baseline))


def in_repo(source):
    return doc("../../skills/{}/SKILL.md".format(source), "Compared with the working tree.")


class CheckRecord(unittest.TestCase):
    def setUp(self):
        self.docs = {"widget": external()}

    def adapted(self):
        return catalog.read(MemoryTree({"docs/skills/{}.md".format(n): t for n, t in self.docs.items()})).adaptations()

    def status(self, records, now=NOW):
        return check_record.status(self.adapted(), records, now)

    def record(self, records=None, url=MATT, now=NOW):
        return check_record.record(self.adapted(), records or {}, url, SHA, now)

    def test_without_a_record_the_check_is_due(self):
        status = self.status({})
        self.assertTrue(status["due"])
        self.assertEqual(status["upstreams"], [dict(url=MATT, due=True, checked_at=None, upstream_sha=None,
                                                    skills=["widget"])])
        self.assertEqual(status["skills"], ["widget"])

    def test_a_check_is_fresh_for_thirty_days(self):
        records = self.record()
        self.assertEqual(records[MATT]["checked_at"], NOW.isoformat())
        self.assertFalse(self.status(records, NOW + timedelta(days=29, hours=23))["due"])
        self.assertTrue(self.status(records, NOW + timedelta(days=30))["due"])

    def test_a_new_baseline_invalidates_a_fresh_record(self):
        records = self.record()
        self.docs["widget"] = external(baseline="b" * 40)
        self.assertTrue(self.status(records)["due"])

    def test_future_or_malformed_records_are_due(self):
        good = self.record()[MATT]
        for bad in [dict(good, checked_at=(NOW + timedelta(days=1)).isoformat()),
                    dict(good, checked_at="2026-11-10T00:00:00"), dict(good, upstream_sha="short"),
                    dict(good, checked_at="yesterday"), {k: v for k, v in good.items() if k != "scope"}, "not a record"]:
            with self.subTest(record=bad):
                self.assertTrue(self.status({MATT: bad})["due"])

    def test_each_upstream_has_its_own_record(self):
        self.docs["other-upstream"] = external(OTHER)
        records = self.record()
        status = self.status(records)
        self.assertTrue(status["due"])
        self.assertEqual({u["url"]: u["due"] for u in status["upstreams"]}, {MATT: False, OTHER: True})
        self.assertFalse(self.status(self.record(records, OTHER))["due"])

    def test_in_repo_adaptations_are_listed_but_never_due(self):
        self.docs["variant"] = in_repo("widget")
        status = self.status(self.record())
        self.assertFalse(status["due"])
        self.assertEqual(status["in_repo"], ["variant"])
        self.assertEqual(status["skills"], ["variant", "widget"])

    def test_without_external_upstreams_nothing_is_due_or_recordable(self):
        self.docs = {"variant": in_repo("widget")}
        self.assertFalse(self.status({})["due"])
        with self.assertRaisesRegex(ValueError, "no skills are adapted"):
            self.record()

    def test_records_need_a_full_sha(self):
        with self.assertRaisesRegex(ValueError, "full upstream commit SHA"):
            check_record.record(self.adapted(), {}, MATT, "abc123", NOW)

    def test_recording_keeps_other_upstreams(self):
        records = self.record({OTHER: "kept"})
        self.assertEqual(records[OTHER], "kept")


if __name__ == "__main__":
    unittest.main()
