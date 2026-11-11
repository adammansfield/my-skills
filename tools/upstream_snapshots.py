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
import subprocess
import sys
import tempfile


UPSTREAM = "https://github.com/mattpocock/skills"
FILES = ("SKILL.md", "agents/openai.yaml")


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout.decode("utf-8")


def prose_lines(text):
    """Yield lines outside fenced blocks, retaining original offsets."""
    fence, offset = None, 0
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
        elif marker:
            fence = marker[1]
        else:
            yield line, offset
        offset += len(line)


def headings(text):
    """Locate ATX headings outside fenced blocks, retaining original offsets."""
    result = []
    for line, offset in prose_lines(text):
        match = re.match(r"^ {0,3}(#{1,6}) +(.+?)\s*#*\s*$", line)
        if match:
            result.append((len(match[1]), match[2], offset, offset + len(line)))
    return result


def section(text, title, level, parent=None):
    lower, upper = (parent[2], parent[1]) if parent else (0, len(text))
    entries = headings(text)
    matches = [h for h in entries if h[0] == level and h[1] == title and lower <= h[2] < upper]
    if len(matches) != 1:
        raise ValueError("expected exactly one {} {} section".format("#" * level, title))
    heading = matches[0]
    end = next((h[2] for h in entries if h[2] > heading[2] and h[0] <= level), len(text))
    return heading[2], min(end, upper), heading[3]


def adaptations(root, names=None):
    results = []
    for doc in sorted((root / "docs/skills").glob("*.md")):
        if names and doc.stem not in names:
            continue
        text = doc.read_bytes().decode("utf-8")
        if not any(h[:2] == (2, "Upstream") for h in headings(text)):
            continue
        try:
            upstream = section(text, "Upstream", 2)
            sources = section(text, "Sources", 3, upstream)
            diff = section(text, "Diff", 3, upstream)
            links = re.findall(re.escape(UPSTREAM) + r"/blob/[^/\s)]+/([^\s)]+/SKILL\.md)", text[sources[2]:sources[1]])
            if len(links) != 1:
                raise ValueError("Sources must contain one unambiguous upstream SKILL.md link")
            source = PurePosixPath(links[0]).parent
            if source.is_absolute() or ".." in source.parts:
                raise ValueError("invalid upstream source path")
            attribution = "".join(line for line, _ in prose_lines(text[diff[2]:diff[1]]))
            baselines = set(re.findall(re.escape(UPSTREAM) + r"/commit/([0-9a-f]{40})(?![0-9a-f])", attribution))
            if len(baselines) != 1:
                raise ValueError("Diff must identify one full upstream baseline SHA")
            results.append(dict(name=doc.stem, doc=doc, text=text, source=str(source), baseline=baselines.pop(), span=diff))
        except ValueError as error:
            raise ValueError("{}: {}".format(doc, error)) from error
    missing = set(names or ()) - {item["name"] for item in results}
    if missing or not results:
        raise ValueError("no upstream documentation found for {}".format(", ".join(sorted(missing)) or "any skills"))
    return results


def patch(before, after, source, local):
    lines = difflib.unified_diff(before.replace("\r\n", "\n").splitlines(keepends=True),
                                 after.replace("\r\n", "\n").splitlines(keepends=True),
                                 fromfile="upstream/" + source, tofile=local)
    return "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)


def prepare(root, upstream, ref, names=None):
    target = git(upstream, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").strip()
    pending, report = [], []
    for item in adaptations(root, names):
        # Fail clearly when a shallow checkout lacks a documented baseline.
        git(upstream, "rev-parse", "--verify", item["baseline"] + "^{commit}")
        content = "### Diff\n\nCompared with [upstream commit `{}`]({}/commit/{}). Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is refreshed during syncing.\n".format(target[:12], UPSTREAM, target)
        source_changed = False
        for filename in FILES:
            source = item["source"] + "/" + filename
            local = "skills/{}/{}".format(item["name"], filename)
            before = git(upstream, "show", target + ":" + source)
            baseline = git(upstream, "show", item["baseline"] + ":" + source)
            source_changed |= before != baseline
            delta = patch(before, (root / local).read_bytes().decode("utf-8"), source, local)
            fence = "`" * max(4, max((len(run) + 1 for run in re.findall(r"`+", delta)), default=4))
            content += "\n#### {}\n\n{}diff\n{}{}\n".format(filename, fence, delta, fence)
        start, end, _ = item["span"]
        newline = "\r\n" if "\r\n" in item["text"] else "\n"
        if end < len(item["text"]):
            content += "\n"
        content = content.replace("\n", newline)
        updated = item["text"][:start] + content + item["text"][end:]
        stale = updated != item["text"]
        if stale:
            pending.append((item["doc"], updated))
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
    path = Path(git(root, "rev-parse", "--git-path", "upstream-check.json").strip())
    return path if path.is_absolute() else root / path


def fingerprint(root):
    scope = [(a["name"], a["source"], a["baseline"]) for a in adaptations(root)]
    return hashlib.sha256(json.dumps(scope).encode()).hexdigest()


def freshness(root, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        record = json.loads(state_path(root).read_bytes().decode("utf-8"))
        checked = datetime.fromisoformat(record["checked_at"])
        if checked.tzinfo is None or checked > now or not re.fullmatch(r"[0-9a-f]{40}", record["upstream_sha"]):
            raise ValueError("invalid check record")
        due = now - checked >= timedelta(days=30) or record["scope"] != fingerprint(root)
        return dict(due=due, checked_at=record["checked_at"], upstream_sha=record["upstream_sha"])
    except (OSError, ValueError, KeyError, TypeError):
        return dict(due=True, checked_at=None, upstream_sha=None)


def record_check(root, sha, now=None):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("record a full upstream commit SHA")
    record = dict(checked_at=(now or datetime.now(timezone.utc)).isoformat(), upstream_sha=sha, scope=fingerprint(root))
    atomic_write(state_path(root), json.dumps(record, indent=2) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-dir", type=Path)
    parser.add_argument("--ref")
    parser.add_argument("--skill", action="append", dest="skills", help="limit snapshot selection; repeat as needed")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--write", action="store_true", help="refresh only Diff sections; default is read-only")
    modes.add_argument("--status", action="store_true", help="report whether the 30-day session check is due; no network access")
    modes.add_argument("--record-check", metavar="SHA", help="record a completed check of ALL adapted skills in local Git state")
    args = parser.parse_args()
    try:
        root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
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
