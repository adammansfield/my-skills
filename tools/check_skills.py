#!/usr/bin/env python3
"""Check skill metadata and intent docs using Python 3.8+ and Git, without dependencies."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

import catalog
from catalog import INTERNAL, SKILLS, WRAPPERS, skill_path
import upstream_snapshots
from repo import IndexTree, WorkingTree, git_list, toplevel


def render_wrapper(frontmatter, source_path):
    """Return the Claude wrapper for an internal skill: its frontmatter verbatim, then a pointer to it."""
    newline = "\r\n" if "\r\n" in frontmatter else "\n"
    pointer = "\nRead and follow `{}` from this repository's root.\n".format(source_path)
    return frontmatter + pointer.replace("\n", newline)


def check(tree):
    """Return error strings for the skills and intent docs in `tree` (see repo)."""
    found = catalog.read(tree)
    if not (found.skills or found.internal or found.wrappers):
        return ["no skills found"]
    problems = (found.problems + _metadata_errors(found) + _wrapper_errors(found)
                + _coverage_errors(tree, found) + _doc_errors(found) + _in_repo_errors(tree, found))
    return ["{}: {}".format(path, message) for path, message in problems]


def _metadata_errors(found):
    # Claude wrappers are rendered from their internal skill, which owns Codex UI metadata.
    errors = []
    for skill in list(found.skills.values()) + list(found.internal.values()):
        try:
            _check_metadata(skill)
        except ValueError as error:
            errors.append((skill.path, str(error)))
    return errors


def require_text(fields, key):
    value = fields.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{} must be a nonempty string".format(".".join(key)))
    return value


def _check_metadata(skill):
    meta, ui = skill.fields, skill.ui
    disabled = None
    if meta is not None:
        name = require_text(meta, ("name",))
        if name != skill.name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise ValueError("name must match its directory and use lowercase words separated by hyphens")
        require_text(meta, ("description",))
        disabled = meta.get(("disable-model-invocation",), False)
        if type(disabled) is not bool:
            raise ValueError("disable-model-invocation must be a boolean")
    if ui is not None:
        require_text(ui, ("interface", "display_name"))
        description = require_text(ui, ("interface", "short_description"))
        if not 25 <= len(description) <= 64:
            raise ValueError("short_description must contain 25–64 characters")
        implicit = ui.get(("policy", "allow_implicit_invocation"), True)
        if type(implicit) is not bool or (disabled is not None and implicit == disabled):
            raise ValueError("allow_implicit_invocation must be the opposite of disable-model-invocation")


def _wrapper_errors(found):
    """Compare each Claude wrapper with the one rendered from its internal skill."""
    errors = []
    for name, source in found.internal.items():
        wrapper = found.wrappers.get(name)
        if source.frontmatter is None or (wrapper and wrapper.text is None):
            continue  # The catalog reported why.
        expected = render_wrapper(source.frontmatter, source.path)
        if not wrapper or wrapper.text != expected:
            path = wrapper.path if wrapper else skill_path(WRAPPERS, name)
            errors.append((path, "Claude wrapper must match {}; expected:\n{}".format(source.path, expected)))
    for name, wrapper in found.wrappers.items():
        if name not in found.internal:
            errors.append((wrapper.path, "wrapper is missing its internal skill: " + skill_path(INTERNAL, name)))
    return errors


def _coverage_errors(tree, found):
    """Require one intent doc and one README bullet per skill under SKILLS."""
    errors = []
    try:
        readme = tree.read("README.md") if "README.md" in tree.paths() else ""
    except (OSError, ValueError) as error:
        return [("README.md", str(error))]
    bullets = [line for line in readme.splitlines() if re.match(r"\s*[-*] ", line)]
    for name, skill in found.skills.items():
        if name not in found.docs:
            errors.append((skill.path, "missing intent doc " + catalog.doc_path(name)))
        if not any("(`{}`)".format(name) in line for line in bullets):
            errors.append((skill.path, "README.md must list (`{}`) in a bullet".format(name)))
    return errors


def _doc_errors(found):
    """Require each intent doc to name a skill, and any skill description its ## Invocation quotes to match."""
    errors = []
    for name, doc in sorted(found.docs.items()):
        skill = found.skills.get(name)
        if not skill:
            errors.append((doc.path, "no skill at " + skill_path(SKILLS, name)))
            continue
        if doc.doc is None or skill.fields is None:
            continue  # The catalog reported why.
        quoted = re.findall(r"\bthe description `([^`]+)`", doc.doc.body("Invocation"))
        if quoted and set(quoted) != {skill.fields.get(("description",))}:
            errors.append((doc.path, "## Invocation quotes a description that differs from " + skill.path))
    return errors


def _in_repo_errors(tree, found):
    """Require each in-repo adaptation's Diff snapshot to match its source's current files."""
    adapted = found.adaptations()
    errors = []
    for item in adapted:
        if item.upstream.repo is not None:
            continue
        cycle = upstream_snapshots.cycle(item, adapted)
        if cycle:
            errors.append((item.path, "in-repo adaptation cycle: " + " -> ".join(cycle)))
            continue
        try:
            if upstream_snapshots.snapshot_in_repo(tree, item) != item.doc.text:
                errors.append((item.path, "stale in-repo Diff snapshot; run python3 tools/upstream_snapshots.py "
                                          "--in-repo --write"))
        except ValueError as error:
            errors.append((item.path, str(error)))
    return errors


def staged_tooling_changed(root):
    # Disable rename detection so moves out of these directories still trigger tests. Python files
    # elsewhere, such as internal skill scripts, are tested from tools/.
    paths = git_list(root, "diff", "--cached", "--name-only", "--no-renames")
    return any(path.startswith(("tools/", ".githooks/")) or path.endswith(".py") for path in paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="check Git's index instead of working files")
    tests = parser.add_mutually_exclusive_group()
    tests.add_argument("--tests", action="store_true", help="also run the working-tree Python test suite")
    tests.add_argument("--tests-if-tools-changed", action="store_true",
                       help="with --staged, run tests only for staged tools/ or .githooks/ changes")
    args = parser.parse_args()
    if args.tests_if_tools_changed and not args.staged:
        parser.error("--tests-if-tools-changed requires --staged")
    root = toplevel(Path.cwd())
    errors = check(IndexTree(root) if args.staged else WorkingTree(root))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Skill metadata and doc checks passed ({}).".format("staged" if args.staged else "working tree"), flush=True)
    if args.tests or (args.tests_if_tools_changed and staged_tooling_changed(root)):
        # A hook inherits the commit's Git environment, such as `git commit -a`'s temporary
        # index; tests run Git in their own repositories and must not write into it.
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        return subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tools",
                               "-p", "test_*.py"], cwd=root, env=env).returncode
    if args.tests_if_tools_changed:
        print("Python tests skipped (no staged tooling or hook changes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
