#!/usr/bin/env python3
"""Check skill metadata and intent docs using Python 3.8+ and Git, without dependencies.

Accepts the repository's YAML subset: space-indented mappings and single-line
scalars. This is a metadata check, not a general-purpose YAML parser.
"""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

import intent_docs
import upstream_snapshots
from repo import IndexTree, WorkingTree, git_list, toplevel


SKILLS, SHARED, WRAPPERS = "skills/", ".agents/skills/", ".claude/skills/"
SKILL_ROOTS = (SKILLS, SHARED, WRAPPERS)


def skill_path(root, name):
    return "{}{}/SKILL.md".format(root, name)


def scalar(value):
    # Strip comments outside quoted values, respecting YAML's doubled apostrophe.
    match = re.fullmatch(r'''("(?:[^"\\]|\\.)*"|'(?:[^']|'')*')(?:\s+#.*)?''', value)
    if match:
        value = match.group(1)
        if value.startswith('"'):
            return json.loads(value)
        return value[1:-1].replace("''", "'")
    value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
    if not value or value[0] in "\"'[{|>!&*" or ": " in value:
        raise ValueError("use a single-line plain or quoted scalar")
    try:
        return json.loads(value)
    except ValueError:
        return value


def mapping(text):
    fields = {}
    parents = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"( *)([A-Za-z_][\w-]*):(?: +(.*))?", line.rstrip())
        if not match:
            raise ValueError("line {}: expected a mapping with single-line values".format(number))
        indent, key, value = len(match[1]), match[2], match[3]
        while parents and parents[-1][0] >= indent:
            parents.pop()
        expected = parents[-1][0] + 2 if parents else 0
        if indent != expected:
            raise ValueError("line {}: expected {} spaces of indentation".format(number, expected))
        path = tuple(item[1] for item in parents) + (key,)
        if path in fields:
            raise ValueError("line {}: duplicate key {}".format(number, ".".join(path)))
        fields[path] = scalar(value) if value and not value.startswith("#") else None
        if fields[path] is None:
            parents.append((indent, key))
    return fields


def skill_document(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("missing YAML frontmatter delimiters")
    end = lines.index("---", 1)
    return mapping("\n".join(lines[1:end])), "\n".join(lines[end + 1:]).strip()


def require_text(fields, key):
    value = fields.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{} must be a nonempty string".format(".".join(key)))
    return value


def render_wrapper(source_text, source_path):
    """Return the Claude wrapper for a shared skill: its frontmatter verbatim, then a pointer to it."""
    lines = source_text.splitlines(keepends=True)
    end = next(i for i in range(1, len(lines)) if lines[i].rstrip("\r\n") == "---")
    newline = "\r\n" if "\r\n" in source_text else "\n"
    pointer = "\nRead and follow `{}` from this repository's root.\n".format(source_path)
    return "".join(lines[:end + 1]) + pointer.replace("\n", newline)


def check(tree):
    """Return error strings for the skills and intent docs in `tree` (see repo.IndexTree, repo.WorkingTree)."""
    paths = set(tree.paths())
    found = [p for p in paths if p.endswith("/SKILL.md") and p.startswith(SKILL_ROOTS)]
    if not found:
        return ["no skills found"]
    skills, misplaced = _skills_by_root(found)
    metadata = _metadata_errors(tree, skills)
    docs = _doc_errors(tree, paths, skills)
    problems = (misplaced + metadata + _wrapper_errors(tree, skills, {path for path, _ in metadata})
                + _coverage_errors(tree, paths, skills) + docs + ([] if docs else _in_repo_errors(tree)))
    return ["{}: {}".format(path, message) for path, message in problems]


def _skills_by_root(paths):
    """Map each skill root to {directory name: SKILL.md path}; report SKILL.md files not at ROOT/NAME/SKILL.md."""
    groups, misplaced = {root: {} for root in SKILL_ROOTS}, []
    for path in sorted(paths):
        root = next(r for r in SKILL_ROOTS if path.startswith(r))
        if path[len(root):].count("/") != 1:
            misplaced.append((path, "skills must be at {}NAME/SKILL.md".format(root)))
        else:
            groups[root][Path(path).parent.name] = path
    return groups, misplaced


def _each(paths, validate):
    """Call `validate(path)` for each path, collecting (path, message) for ValueError or OSError."""
    errors = []
    for path in paths:
        try:
            validate(path)
        except (ValueError, OSError) as error:
            errors.append((path, str(error)))
    return errors


def _metadata_errors(tree, skills):
    # Claude wrappers are rendered from their shared skill, which owns Codex UI metadata.
    return _each(sorted(list(skills[SKILLS].values()) + list(skills[SHARED].values())),
                 lambda path: _check_metadata(tree, path))


def _check_metadata(tree, path):
    meta, _ = skill_document(tree.read(path))
    name = require_text(meta, ("name",))
    if name != Path(path).parent.name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("name must match its directory and use lowercase words separated by hyphens")
    require_text(meta, ("description",))
    disabled = meta.get(("disable-model-invocation",), False)
    if type(disabled) is not bool:
        raise ValueError("disable-model-invocation must be a boolean")
    ui = mapping(tree.read(Path(path).parent.as_posix() + "/agents/openai.yaml"))
    require_text(ui, ("interface", "display_name"))
    description = require_text(ui, ("interface", "short_description"))
    if not 25 <= len(description) <= 64:
        raise ValueError("short_description must contain 25–64 characters")
    implicit = ui.get(("policy", "allow_implicit_invocation"), True)
    if type(implicit) is not bool or implicit == disabled:
        raise ValueError("allow_implicit_invocation must be the opposite of disable-model-invocation")


def _wrapper_errors(tree, skills, invalid_sources):
    """Compare each Claude wrapper with the one rendered from its shared skill, skipping `invalid_sources`."""
    errors = []
    shared, wrappers = skills[SHARED], skills[WRAPPERS]
    for name, source in sorted(shared.items()):
        if source in invalid_sources:
            continue
        expected = render_wrapper(tree.read(source), source)
        wrapper = wrappers.get(name, skill_path(WRAPPERS, name))
        if name not in wrappers or tree.read(wrapper) != expected:
            errors.append((wrapper, "Claude wrapper must match {}; expected:\n{}".format(source, expected)))
    for name, wrapper in sorted(wrappers.items()):
        if name not in shared:
            errors.append((wrapper, "wrapper is missing its shared skill: " + skill_path(SHARED, name)))
    return errors


def _coverage_errors(tree, paths, skills):
    """Require one intent doc and one README bullet per skill under SKILLS."""
    errors = []
    bullets = [line for line in (tree.read("README.md") if "README.md" in paths else "").splitlines()
               if re.match(r"\s*[-*] ", line)]
    for name, path in sorted(skills[SKILLS].items()):
        if "docs/skills/{}.md".format(name) not in paths:
            errors.append((path, "missing intent doc docs/skills/{}.md".format(name)))
        if not any("(`{}`)".format(name) in line for line in bullets):
            errors.append((path, "README.md must list (`{}`) in a bullet".format(name)))
    return errors


def _doc_errors(tree, paths, skills):
    """Validate each intent doc and any skill description its ## Invocation quotes."""
    return _each(sorted(p for p in paths if intent_docs.PATH.fullmatch(p)),
                 lambda path: _check_doc(tree, path, skills))


def _check_doc(tree, path, skills):
    skill = skills[SKILLS].get(Path(path).stem)
    if not skill:
        raise ValueError("no skill at " + skill_path(SKILLS, Path(path).stem))
    doc = intent_docs.parse(tree.read(path))
    quoted = re.findall(r"\bthe description `([^`]+)`", doc.body("Invocation"))
    if quoted and set(quoted) != {skill_document(tree.read(skill))[0].get(("description",))}:
        raise ValueError("## Invocation quotes a description that differs from " + skill)


def _in_repo_errors(tree):
    """Require each in-repo adaptation's Diff snapshot to match its source's current files."""
    try:
        pending, _ = upstream_snapshots.prepare_in_repo(tree)
    except (ValueError, OSError) as error:
        return [("docs/skills", str(error))]
    return [(path, "stale in-repo Diff snapshot; run python3 tools/upstream_snapshots.py --in-repo --write")
            for path, _ in pending]


def staged_tooling_changed(root):
    # Disable rename detection so moves out of these directories still trigger tests.
    paths = git_list(root, "diff", "--cached", "--name-only", "--no-renames")
    return any(path.startswith(("tools/", ".githooks/")) for path in paths)


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
        return subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tools",
                               "-p", "test_*.py"], cwd=root).returncode
    if args.tests_if_tools_changed:
        print("Python tests skipped (no staged tooling or hook changes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
