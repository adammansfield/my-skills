#!/usr/bin/env python3
"""Check or refresh upstream Diff snapshots, and report or record upstream checks. Python 3.8+, standard library only.

Supply a local Git checkout containing the target and documented baseline commits.
This tool does not fetch upstream or decide which changes to adopt.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import difflib
import json
from pathlib import Path
import sys
from typing import List, Optional

import catalog
import check_record
import intent_docs
import repo


def _catalog(tree):
    """Return the Skill catalog of `tree`; raise ValueError naming the first adapted or unreadable doc that
    fails to parse. A readable doc without ## Upstream is not an adapted skill, so a broken one is left
    to the pre-commit check."""
    skill_catalog = catalog.read(tree)
    for _, doc in sorted(skill_catalog.docs.items()):
        if doc.parsed is None and doc.declares_upstream is not False:
            raise ValueError("{}: {}".format(doc.path, skill_catalog.problem(doc.path)))
    return skill_catalog


def adaptations(tree):
    """Return the adapted skills in `tree` as catalog.Doc values (see _catalog for errors)."""
    return _catalog(tree).adaptations()


def _select(adapted, names, repo_url):
    """Return the adapted skills from `repo_url` (None for in-repo upstreams), limited to `names`."""
    missing = set(names or ()) - {item.name for item in adapted}
    if missing:
        raise ValueError("no upstream documentation found for {}".format(", ".join(sorted(missing))))
    selected = [item for item in adapted if item.upstream.repo == repo_url and (not names or item.name in names)]
    others = set(names or ()) - {item.name for item in selected}
    if others:
        raise ValueError("not adapted from {}: {}".format(repo_url or "an in-repo upstream", ", ".join(sorted(others))))
    return selected


def patch(before, after, source, local):
    lines = difflib.unified_diff(before.replace("\r\n", "\n").splitlines(keepends=True),
                                 after.replace("\r\n", "\n").splitlines(keepends=True),
                                 fromfile="upstream/" + source, tofile=local)
    return "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)


def _sources(tree, item, role):
    """Return the texts of the item's upstream FILES in `tree`, where `role` names that tree in errors."""
    texts = []
    for filename in catalog.FILES:
        path = item.upstream.source + "/" + filename
        try:
            texts.append(tree.read(path))
        except (OSError, ValueError) as error:
            raise ValueError("missing {} file {}".format(role, path)) from error
    return texts


def _snapshot(item, tree, sources, target):
    """Return the item's doc text with its Diff rebuilt from upstream `sources` against its files in `tree`."""
    patches = []
    for filename, before in zip(catalog.FILES, sources):
        local = catalog.skill_path(catalog.SKILLS, item.name, filename)
        try:
            after = tree.read(local)
        except (OSError, ValueError) as error:
            raise ValueError("missing local file " + local) from error
        patches.append((filename, patch(before, after, item.upstream.source + "/" + filename, local)))
    return intent_docs.with_diff(item.parsed, target, patches)


def snapshot_in_repo(tree, item, skill_catalog):
    """Return the in-repo adaptation's doc text with its Diff rebuilt from its source's files in `tree`.

    Raise ValueError when its upstream chain leads back to it or a file is missing.
    """
    chain = skill_catalog.cycle(item)
    if chain:
        raise ValueError("in-repo adaptation cycle: " + " -> ".join(chain))
    return _snapshot(item, tree, _sources(tree, item, "in-repo upstream"), None)


def _snapshot_external(item, tree, current, target, at):
    try:
        baseline = at(item.upstream.baseline)  # A shallow checkout may lack a documented baseline.
    except ValueError as error:
        raise ValueError("baseline {} is not in the upstream checkout: {}".format(
            item.upstream.baseline, error)) from error
    sources = _sources(current, item, "upstream")
    fields = dict(baseline=item.upstream.baseline, source_changed=sources != _sources(baseline, item, "baseline"))
    return _snapshot(item, tree, sources, target), fields


def _compare(selected, snapshot):
    """Return (pending, report) from `snapshot(item)` -> (updated text, report fields); errors name the doc."""
    pending, report = [], []
    for item in selected:
        try:
            updated, fields = snapshot(item)
        except ValueError as error:
            raise ValueError("{}: {}".format(item.path, error)) from error
        stale = updated != item.parsed.text
        if stale:
            pending.append((item.path, updated))
        report.append(dict(skill=item.name, **fields, snapshot_stale=stale))
    return pending, report


def prepare(tree, url, target, at, names=None):
    """Compare the skills adapted from the external upstream `url` with its tree at commit `target`.

    `at(commit)` returns the upstream tree at a full commit SHA, raising ValueError for an unknown commit.
    Return (pending, report): pending is a list of (doc path, updated text) for stale snapshots.
    """
    selected = _select(adaptations(tree), names, url)
    if not selected:
        raise ValueError("no skills are adapted from " + url)
    current = at(target)
    return _compare(selected, lambda item: _snapshot_external(item, tree, current, target, at))


def prepare_in_repo(tree, names=None):
    """Compare skills adapted from in-repo upstreams with their sources' current files in `tree`.

    Return (pending, report): pending is a list of (doc path, updated text) for stale snapshots.
    """
    skill_catalog = _catalog(tree)
    return _compare(_select(skill_catalog.adaptations(), names, None),
                    lambda item: (snapshot_in_repo(tree, item, skill_catalog), dict(source=item.upstream.source)))


@dataclass(frozen=True)
class Status:
    """Report whether each external upstream's check is due."""

    def run(self, tree, now):
        return 0, check_record.status(adaptations(tree), check_record.load(tree.root), now)


@dataclass(frozen=True)
class Record:
    """Record a completed check of every skill adapted from `upstream` at commit `sha`."""
    upstream: str
    sha: str

    def run(self, tree, now):
        records = check_record.record(adaptations(tree), check_record.load(tree.root), self.upstream, self.sha, now)
        check_record.save(tree.root, records)
        return 0, records[self.upstream]


@dataclass(frozen=True)
class InRepoSnapshots:
    """Check, or with `write` refresh, the Diff snapshots of skills adapted from in-repo upstreams."""
    skills: Optional[List[str]]
    write: bool

    def run(self, tree, now):
        return _finish(tree, prepare_in_repo(tree, self.skills), self.write)


@dataclass(frozen=True)
class ExternalSnapshots:
    """Check, or with `write` refresh, the Diff snapshots of skills adapted from `upstream` at `ref`."""
    upstream: str
    upstream_dir: Path
    ref: str
    skills: Optional[List[str]]
    write: bool

    def run(self, tree, now):
        target = repo.CommitTree(self.upstream_dir, self.ref).commit
        compared = prepare(tree, self.upstream, target, lambda commit: repo.CommitTree(self.upstream_dir, commit),
                           self.skills)
        return _finish(tree, compared, self.write, target)


def _finish(tree, compared, write, target=None):
    """Write stale snapshots when asked; every selected doc was validated before any is written."""
    pending, report = compared
    if write:
        for path, content in pending:
            repo.atomic_write(tree.root / path, content)
    output = dict(skills=report, written=len(pending) if write else 0)
    if target:
        output = dict(target=target, **output)
    return int(bool(pending) and not write), output


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", metavar="URL", help="the external upstream repository, as linked in ### Sources")
    parser.add_argument("--upstream-dir", type=Path)
    parser.add_argument("--ref")
    parser.add_argument("--skill", action="append", dest="skills", help="limit snapshot selection; repeat as needed")
    parser.add_argument("--in-repo", action="store_true",
                        help="compare skills adapted from in-repo upstreams with their working-tree sources")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--write", action="store_true", help="refresh only Diff sections; default is read-only")
    modes.add_argument("--status", action="store_true",
                       help="report whether each external upstream's 30-day check is due and list adapted skills; "
                            "no network access")
    modes.add_argument("--record-check", metavar="SHA",
                       help="with --upstream, record a completed check of ALL skills adapted from it in local Git state")
    return parser


def plan(argv):
    """Return the command for `argv` (Status, Record, InRepoSnapshots or ExternalSnapshots), each with
    `run(tree, now) -> (exit status, JSON output)`; raise ValueError for an invalid combination of options."""
    args = _parser().parse_args(argv)
    if args.status or args.record_check:
        if args.upstream_dir or args.ref or args.skills or args.in_repo:
            raise ValueError("--status and --record-check cannot be combined with snapshot options")
        if args.status and args.upstream:
            raise ValueError("--status reports every upstream; omit --upstream")
        if args.record_check and not args.upstream:
            raise ValueError("--record-check requires --upstream")
        return Status() if args.status else Record(args.upstream, args.record_check)
    if args.in_repo:
        if args.upstream or args.upstream_dir or args.ref:
            raise ValueError("--in-repo cannot be combined with external upstream options")
        return InRepoSnapshots(args.skills, args.write)
    if not args.upstream or not args.upstream_dir or not args.ref:
        raise ValueError("snapshot mode requires --upstream, --upstream-dir, and --ref, or --in-repo")
    return ExternalSnapshots(args.upstream, args.upstream_dir, args.ref, args.skills, args.write)


def main(argv=None):
    try:
        command = plan(argv)
    except ValueError as error:
        _parser().error(str(error))
    try:
        status, output = command.run(repo.WorkingTree(repo.toplevel(Path.cwd())), datetime.now(timezone.utc))
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(output, indent=2))
    return status


if __name__ == "__main__":
    sys.exit(main())
