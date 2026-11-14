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


def adaptations(tree):
    """Return the adapted skills in `tree` as catalog.Doc values.

    Raise ValueError naming the first adapted or unreadable doc that fails to parse. A readable doc
    without ## Upstream is not an adapted skill, so a broken one is left to the pre-commit check.
    """
    found = catalog.read(tree)
    for _, doc in sorted(found.docs.items()):
        if doc.doc is None and doc.adapted is not False:
            raise ValueError("{}: {}".format(doc.path, found.problem(doc.path)))
    return found.adaptations()


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


def _read(tree, path, role):
    try:
        return tree.read(path)
    except (OSError, ValueError) as error:
        raise ValueError("missing {} file {}".format(role, path)) from error


def _snapshot(item, tree, source, target):
    """Return the item's doc text with its Diff rebuilt from `source` (a tree) against the local files in `tree`."""
    patches = []
    for filename in catalog.FILES:
        upstream = item.upstream.source + "/" + filename
        local = catalog.skill_path(catalog.SKILLS, item.name, filename)
        before = _read(source, upstream, "upstream" if target else "in-repo upstream")
        patches.append((filename, patch(before, _read(tree, local, "local"), upstream, local)))
    return intent_docs.with_diff(item.doc, target, patches)


def snapshot_in_repo(tree, item):
    """Return the in-repo adaptation's doc text with its Diff rebuilt from its source's files in `tree`."""
    return _snapshot(item, tree, tree, None)


def _snapshot_external(item, tree, current, target, at):
    try:
        baseline = at(item.upstream.baseline)  # A shallow checkout may lack a documented baseline.
    except ValueError as error:
        raise ValueError("baseline {} is not in the upstream checkout: {}".format(
            item.upstream.baseline, error)) from error
    sources = [item.upstream.source + "/" + filename for filename in catalog.FILES]
    source_changed = ([_read(current, path, "upstream") for path in sources]
                      != [_read(baseline, path, "baseline") for path in sources])
    fields = dict(baseline=item.upstream.baseline, source_changed=source_changed)
    return _snapshot(item, tree, current, target), fields


def _compare(selected, snapshot):
    """Return (pending, report) from `snapshot(item)` -> (updated text, report fields); errors name the doc."""
    pending, report = [], []
    for item in selected:
        try:
            updated, fields = snapshot(item)
        except ValueError as error:
            raise ValueError("{}: {}".format(item.path, error)) from error
        stale = updated != item.doc.text
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
    adapted = adaptations(tree)
    for item in adapted:
        chain = cycle(item, adapted)
        if chain:
            raise ValueError("{}: in-repo adaptation cycle: {}".format(item.path, " -> ".join(chain)))
    return _compare(_select(adapted, names, None),
                    lambda item: (snapshot_in_repo(tree, item), dict(source=item.upstream.source)))


def cycle(item, adapted):
    """Return the chain of in-repo upstreams that leads from `item` back to it, or None."""
    sources = {a.name: a.upstream.skill for a in adapted if a.upstream.repo is None}
    chain = [item.name]
    while chain[-1] in sources:
        chain.append(sources[chain[-1]])
        if chain[-1] in chain[:-1]:
            return chain if chain[-1] == item.name else None
    return None


@dataclass(frozen=True)
class Plan:
    """One resolved command: `mode` is "status", "record", "external" or "in-repo"."""
    mode: str
    upstream: Optional[str] = None
    upstream_dir: Optional[Path] = None
    ref: Optional[str] = None
    skills: Optional[List[str]] = None
    write: bool = False
    sha: Optional[str] = None


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
    """Return the Plan for command-line `argv`; raise ValueError for an invalid combination of options."""
    args = _parser().parse_args(argv)
    if args.status or args.record_check:
        if args.upstream_dir or args.ref or args.skills or args.in_repo:
            raise ValueError("freshness modes cannot be combined with snapshot options")
        if args.status and args.upstream:
            raise ValueError("--status reports every upstream; omit --upstream")
        if args.record_check and not args.upstream:
            raise ValueError("--record-check requires --upstream")
        return Plan("status") if args.status else Plan("record", upstream=args.upstream, sha=args.record_check)
    if args.in_repo:
        if args.upstream or args.upstream_dir or args.ref:
            raise ValueError("--in-repo cannot be combined with external upstream options")
        return Plan("in-repo", skills=args.skills, write=args.write)
    if not args.upstream or not args.upstream_dir or not args.ref:
        raise ValueError("snapshot mode requires --upstream, --upstream-dir, and --ref, or --in-repo")
    return Plan("external", upstream=args.upstream, upstream_dir=args.upstream_dir, ref=args.ref,
                skills=args.skills, write=args.write)


def run(plan, tree, now):
    """Carry out `plan` on the working tree `tree`; return (exit status, JSON output)."""
    if plan.mode in ("status", "record"):
        adapted, records = adaptations(tree), check_record.load(tree.root)
        if plan.mode == "status":
            return 0, check_record.status(adapted, records, now)
        records = check_record.record(adapted, records, plan.upstream, plan.sha, now)
        check_record.save(tree.root, records)
        return 0, records[plan.upstream]
    if plan.mode == "in-repo":
        target, (pending, report) = None, prepare_in_repo(tree, plan.skills)
    else:
        target = repo.CommitTree(plan.upstream_dir, plan.ref).commit
        pending, report = prepare(tree, plan.upstream, target,
                                  lambda commit: repo.CommitTree(plan.upstream_dir, commit), plan.skills)
    # Every selected document is validated before any is written.
    if plan.write:
        for path, content in pending:
            repo.atomic_write(tree.root / path, content)
    output = dict(skills=report, written=len(pending) if plan.write else 0)
    if target:
        output = dict(target=target, **output)
    return int(bool(pending) and not plan.write), output


def main(argv=None):
    try:
        resolved = plan(argv)
    except ValueError as error:
        _parser().error(str(error))
    try:
        status, output = run(resolved, repo.WorkingTree(repo.toplevel(Path.cwd())), datetime.now(timezone.utc))
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(output, indent=2))
    return status


if __name__ == "__main__":
    sys.exit(main())
