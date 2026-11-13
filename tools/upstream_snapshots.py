#!/usr/bin/env python3
"""Check or refresh upstream diff snapshots. Python 3.8+, standard library only.

Supply a local Git checkout containing the target and documented baseline commits.
This tool does not fetch upstream or decide which changes to adopt.
"""

import argparse
from datetime import datetime, timedelta, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile

import intent_docs
import repo


FILES = ("SKILL.md", "agents/openai.yaml")


def adaptations(tree, names=None):
    """Return the adapted skills in `tree` (see repo.WorkingTree), optionally limited to `names`."""
    results = []
    for path in tree.paths():
        name = PurePosixPath(path).stem
        if not intent_docs.PATH.fullmatch(path) or (names and name not in names):
            continue
        text = tree.read(path)
        if not intent_docs.declares_upstream(text):
            continue  # Not an adapted skill; the pre-commit check validates it instead.
        try:
            parsed = intent_docs.parse(text)
        except ValueError as error:
            raise ValueError("{}: {}".format(path, error)) from error
        results.append(dict(name=name, path=path, doc=parsed, repo=parsed.upstream.repo,
                            source=parsed.upstream.source, baseline=parsed.upstream.baseline))
    missing = set(names or ()) - {item["name"] for item in results}
    if missing:
        raise ValueError("no upstream documentation found for {}".format(", ".join(sorted(missing))))
    return results


def _select(adapted, names, repo_url):
    """Return the adapted skills from `repo_url` (None for in-repo upstreams), limited to `names`."""
    missing = set(names or ()) - {item["name"] for item in adapted}
    if missing:
        raise ValueError("no upstream documentation found for {}".format(", ".join(sorted(missing))))
    selected = [item for item in adapted if item["repo"] == repo_url and (not names or item["name"] in names)]
    others = set(names or ()) - {item["name"] for item in selected}
    if others:
        raise ValueError("not adapted from {}: {}".format(repo_url or "an in-repo upstream", ", ".join(sorted(others))))
    return selected


def patch(before, after, source, local):
    lines = difflib.unified_diff(before.replace("\r\n", "\n").splitlines(keepends=True),
                                 after.replace("\r\n", "\n").splitlines(keepends=True),
                                 fromfile="upstream/" + source, tofile=local)
    return "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)


def prepare(root, url, upstream, ref, names=None):
    """Compare the skills adapted from the external upstream `url` with its checkout at `ref`."""
    target = repo.git(upstream, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").strip()
    tree = repo.WorkingTree(root)
    selected = _select(adaptations(tree), names, url)
    if not selected:
        raise ValueError("no skills are adapted from " + url)
    pending, report = [], []
    for item in selected:
        # Fail clearly when a shallow checkout lacks a documented baseline.
        repo.git(upstream, "rev-parse", "--verify", item["baseline"] + "^{commit}")
        source_changed, patches = False, []
        for filename in FILES:
            source = item["source"] + "/" + filename
            local = "skills/{}/{}".format(item["name"], filename)
            before = repo.git(upstream, "show", target + ":" + source)
            baseline = repo.git(upstream, "show", item["baseline"] + ":" + source)
            source_changed |= before != baseline
            patches.append((filename, patch(before, tree.read(local), source, local)))
        updated = intent_docs.with_diff(item["doc"], target, patches)
        stale = updated != item["doc"].text
        if stale:
            pending.append((item["path"], updated))
        report.append(dict(skill=item["name"], baseline=item["baseline"], source_changed=source_changed, snapshot_stale=stale))
    return target, pending, report


def prepare_in_repo(tree, names=None):
    """Compare skills adapted from in-repo upstreams with their sources' current files in `tree`.

    Return (pending, report): pending is a list of (doc path, updated text) for stale snapshots.
    """
    adapted = adaptations(tree)
    _reject_cycles(adapted)
    selected = _select(adapted, names, None)
    pending, report = [], []
    for item in selected:
        patches = []
        for filename in FILES:
            source = item["source"] + "/" + filename
            local = "skills/{}/{}".format(item["name"], filename)
            try:
                before = tree.read(source)
            except (OSError, ValueError) as error:
                raise ValueError("{}: missing in-repo upstream file {}".format(item["path"], source)) from error
            patches.append((filename, patch(before, tree.read(local), source, local)))
        updated = intent_docs.with_diff(item["doc"], None, patches)
        stale = updated != item["doc"].text
        if stale:
            pending.append((item["path"], updated))
        report.append(dict(skill=item["name"], source=item["source"], snapshot_stale=stale))
    return pending, report


def _reject_cycles(items):
    sources = {item["name"]: PurePosixPath(item["source"]).name for item in items if item["repo"] is None}
    for start in sorted(sources):
        chain = [start]
        while chain[-1] in sources:
            chain.append(sources[chain[-1]])
            if chain[-1] in chain[:-1]:
                if chain[-1] == start:
                    raise ValueError("in-repo adaptation cycle: " + " -> ".join(chain))
                break


def atomic_write(path, content):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content.encode("utf-8"))
    try:
        if path.exists():
            temporary.chmod(stat.S_IMODE(path.stat().st_mode))
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def state_path(root):
    path = Path(repo.git(root, "rev-parse", "--git-path", "upstream-check.json").strip())
    return path if path.is_absolute() else root / path


def fingerprint(adapted):
    scope = [(a["name"], a["source"], a["baseline"]) for a in adapted]
    return hashlib.sha256(json.dumps(scope).encode()).hexdigest()


def _external(adapted):
    """Map each external upstream URL to the adapted skills it supplies."""
    groups = {}
    for item in adapted:
        if item["repo"]:
            groups.setdefault(item["repo"], []).append(item)
    return groups


def _records(root):
    try:
        records = json.loads(state_path(root).read_bytes().decode("utf-8"))["upstreams"]
        return records if isinstance(records, dict) else {}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def _upstream_status(url, adapted, record, now):
    skills = [a["name"] for a in adapted]
    try:
        checked = datetime.fromisoformat(record["checked_at"])
        if checked.tzinfo is None or checked > now or not re.fullmatch(r"[0-9a-f]{40}", record["upstream_sha"]):
            raise ValueError("invalid check record")
        due = now - checked >= timedelta(days=30) or record["scope"] != fingerprint(adapted)
        return dict(url=url, due=due, checked_at=record["checked_at"], upstream_sha=record["upstream_sha"], skills=skills)
    except (ValueError, KeyError, TypeError):
        return dict(url=url, due=True, checked_at=None, upstream_sha=None, skills=skills)


def freshness(root, now=None):
    """Report whether each external upstream's 30-day check is due.

    An unreadable check record means due; an intent doc that fails to parse raises ValueError.
    In-repo adaptations are listed but never due: the pre-commit check keeps them current.
    """
    now = now or datetime.now(timezone.utc)
    adapted = adaptations(repo.WorkingTree(root))
    records = _records(root)
    upstreams = [_upstream_status(url, items, records.get(url), now) for url, items in sorted(_external(adapted).items())]
    return dict(due=any(u["due"] for u in upstreams), upstreams=upstreams,
                in_repo=[a["name"] for a in adapted if a["repo"] is None], skills=[a["name"] for a in adapted])


def record_check(root, url, sha, now=None):
    """Record a completed check of every skill adapted from the external upstream `url`."""
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("record a full upstream commit SHA")
    adapted = _external(adaptations(repo.WorkingTree(root))).get(url)
    if not adapted:
        raise ValueError("no skills are adapted from " + str(url))
    records = _records(root)
    records[url] = dict(checked_at=(now or datetime.now(timezone.utc)).isoformat(), upstream_sha=sha,
                        scope=fingerprint(adapted))
    atomic_write(state_path(root), json.dumps(dict(upstreams=records), indent=2) + "\n")
    return records[url]


def main():
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
    args = parser.parse_args()
    try:
        root = repo.toplevel(Path.cwd())
        if args.status or args.record_check:
            if args.upstream_dir or args.ref or args.skills or args.in_repo:
                parser.error("freshness modes cannot be combined with snapshot options")
            if args.status and args.upstream:
                parser.error("--status reports every upstream; omit --upstream")
            if args.record_check and not args.upstream:
                parser.error("--record-check requires --upstream")
            output = freshness(root) if args.status else record_check(root, args.upstream, args.record_check)
        else:
            if args.in_repo:
                if args.upstream or args.upstream_dir or args.ref:
                    parser.error("--in-repo cannot be combined with external upstream options")
                target, (pending, report) = None, prepare_in_repo(repo.WorkingTree(root), args.skills)
            else:
                if not args.upstream or not args.upstream_dir or not args.ref:
                    parser.error("snapshot mode requires --upstream, --upstream-dir, and --ref, or --in-repo")
                target, pending, report = prepare(root, args.upstream, args.upstream_dir, args.ref, args.skills)
            # Validate every selected document before writing any of them.
            if args.write:
                for path, content in pending:
                    atomic_write(root / path, content)
            output = dict(skills=report, written=len(pending) if args.write else 0)
            if target:
                output = dict(target=target, **output)
            print(json.dumps(output, indent=2))
            return int(bool(pending) and not args.write)
        print(json.dumps(output, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
