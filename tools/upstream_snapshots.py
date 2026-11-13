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
from pathlib import Path
import re
import stat
import sys
import tempfile

import intent_docs
import repo


FILES = ("SKILL.md", "agents/openai.yaml")


def adaptations(root, names=None):
    results, tree = [], repo.WorkingTree(root)
    for path in tree.paths():
        doc = root / path
        if not intent_docs.PATH.fullmatch(path) or (names and doc.stem not in names):
            continue
        text = tree.read(path)
        if not intent_docs.declares_upstream(text):
            continue  # The pre-commit check validates docs that sync does not use.
        try:
            parsed = intent_docs.parse(text)
        except ValueError as error:
            raise ValueError("{}: {}".format(doc, error)) from error
        results.append(dict(name=doc.stem, path=doc, doc=parsed,
                            source=parsed.upstream.source, baseline=parsed.upstream.baseline))
    missing = set(names or ()) - {item["name"] for item in results}
    if missing:
        raise ValueError("no upstream documentation found for {}".format(", ".join(sorted(missing))))
    return results


def patch(before, after, source, local):
    lines = difflib.unified_diff(before.replace("\r\n", "\n").splitlines(keepends=True),
                                 after.replace("\r\n", "\n").splitlines(keepends=True),
                                 fromfile="upstream/" + source, tofile=local)
    return "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)


def prepare(root, upstream, ref, names=None):
    target = repo.git(upstream, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").strip()
    pending, report = [], []
    tree = repo.WorkingTree(root)
    selected = adaptations(root, names)
    if not selected:
        raise ValueError("no upstream documentation found for any skills")
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


def freshness(root, now=None):
    """Report whether the 30-day check is due.

    An unreadable check record means due; an intent doc that fails to parse raises ValueError.
    """
    now = now or datetime.now(timezone.utc)
    adapted = adaptations(root)
    scope, skills = fingerprint(adapted), [a["name"] for a in adapted]
    try:
        record = json.loads(state_path(root).read_bytes().decode("utf-8"))
        checked = datetime.fromisoformat(record["checked_at"])
        if checked.tzinfo is None or checked > now or not re.fullmatch(r"[0-9a-f]{40}", record["upstream_sha"]):
            raise ValueError("invalid check record")
        due = now - checked >= timedelta(days=30) or record["scope"] != scope
        return dict(due=due, checked_at=record["checked_at"], upstream_sha=record["upstream_sha"], skills=skills)
    except (OSError, ValueError, KeyError, TypeError):
        return dict(due=True, checked_at=None, upstream_sha=None, skills=skills)


def record_check(root, sha, now=None):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("record a full upstream commit SHA")
    record = dict(checked_at=(now or datetime.now(timezone.utc)).isoformat(), upstream_sha=sha, scope=fingerprint(adaptations(root)))
    atomic_write(state_path(root), json.dumps(record, indent=2) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-dir", type=Path)
    parser.add_argument("--ref")
    parser.add_argument("--skill", action="append", dest="skills", help="limit snapshot selection; repeat as needed")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--write", action="store_true", help="refresh only Diff sections; default is read-only")
    modes.add_argument("--status", action="store_true",
                       help="report whether the 30-day session check is due and list adapted skills; no network access")
    modes.add_argument("--record-check", metavar="SHA", help="record a completed check of ALL adapted skills in local Git state")
    args = parser.parse_args()
    try:
        root = Path(repo.git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
        if args.status or args.record_check:
            if args.upstream_dir or args.ref or args.skills:
                parser.error("freshness modes cannot be combined with snapshot options")
            output = freshness(root) if args.status else record_check(root, args.record_check)
        else:
            if not args.upstream_dir or not args.ref:
                parser.error("snapshot mode requires --upstream-dir and --ref")
            target, pending, report = prepare(root, args.upstream_dir, args.ref, args.skills)
            # Validate every selected document before writing any of them.
            if args.write:
                for path, content in pending:
                    atomic_write(path, content)
            output = dict(target=target, skills=report, written=len(pending) if args.write else 0)
            print(json.dumps(output, indent=2))
            return int(bool(pending) and not args.write)
        print(json.dumps(output, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
