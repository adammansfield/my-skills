#!/usr/bin/env python3
"""Link this checkout's skills into local agent skill folders, using Python 3.8+ and only the standard library.

Each `skills/NAME` is linked from the hub (`~/.agents/skills/NAME`), and each hub entry from every agent
folder, so edits in the checkout are live. Links left by renamed or removed skills are removed. Real
folders and links to elsewhere are reported and left in place. On Windows, a directory junction is used
when creating a symlink is not permitted.
"""

import argparse
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[4]


def link_target(path):
    """Return the absolute target of a symlink or junction at `path`, or None for anything else."""
    try:
        target = os.readlink(str(path))
    except (OSError, ValueError):
        return None
    if target.startswith("\\\\?\\"):
        target = target[4:]
    return Path(os.path.normpath(os.path.join(str(path.parent), target)))


def make_link(path, target):
    try:
        os.symlink(str(target), str(path), target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        import _winapi
        _winapi.CreateJunction(str(target), str(path))


def remove_link(path):
    try:
        os.unlink(str(path))
    except OSError:
        os.rmdir(str(path))  # Windows removes directory symlinks and junctions with rmdir.


def inside(path, folder):
    return os.path.normcase(str(path)).startswith(os.path.normcase(str(folder)) + os.sep)


def sync(repo, hub, agent_dirs, dry_run=False):
    """Link repo skills through `hub` into each of `agent_dirs`; return (actions, warnings) as strings."""
    repo, hub = Path(os.path.abspath(str(repo))), Path(os.path.abspath(str(hub)))
    skills = sorted(p.parent.name for p in (repo / "skills").glob("*/SKILL.md"))
    actions, warnings = [], []

    def ensure(path, target):
        current = link_target(path)
        if current is not None and os.path.normcase(str(current)) == os.path.normcase(str(target)):
            return
        if current is not None or path.exists():
            warnings.append("skipped {}: already exists as {}".format(path, current or "a real folder"))
            return
        actions.append("link {} -> {}".format(path, target))
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            make_link(path, target)

    def prune(folder, owned):
        for path in sorted(folder.iterdir()) if folder.is_dir() else []:
            target = link_target(path)
            if target is not None and inside(target, owned) and target.name not in skills and not target.exists():
                actions.append("remove {} (missing {})".format(path, target))
                if not dry_run:
                    remove_link(path)

    prune(hub, repo / "skills")
    for name in skills:
        ensure(hub / name, repo / "skills" / name)
    for folder in agent_dirs:
        folder = Path(os.path.abspath(str(folder)))
        prune(folder, hub)
        for name in skills:
            ensure(folder / name, hub / name)
    return actions, warnings


def default_agent_dirs():
    config = os.environ.get("CLAUDE_CONFIG_DIR")
    return [Path(config) / "skills" if config else Path.home() / ".claude" / "skills"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hub", type=Path, default=Path.home() / ".agents" / "skills",
                        help="folder that links to the checkout (default: ~/.agents/skills)")
    parser.add_argument("--agent-dir", type=Path, action="append",
                        help="agent skills folder to link into; repeatable "
                             "(default: $CLAUDE_CONFIG_DIR/skills, else ~/.claude/skills)")
    parser.add_argument("--dry-run", action="store_true", help="report changes without making them")
    args = parser.parse_args()
    actions, warnings = sync(REPO, args.hub, args.agent_dir or default_agent_dirs(), args.dry_run)
    for line in actions:
        print(("would " if args.dry_run else "") + line)
    for line in warnings:
        print(line, file=sys.stderr)
    if not actions:
        print("Links are current.")
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
