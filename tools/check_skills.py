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


SKILL_ROOTS = ("skills/", ".agents/skills/", ".claude/skills/")


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


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


def check(root, staged=False):
    if staged:
        paths = git(root, "ls-files", "--cached", "-z").decode().split("\0")
        read = lambda path: git(root, "show", ":" + path).decode("utf-8")
    else:
        paths = [p.relative_to(root).as_posix() for prefix in SKILL_ROOTS
                 for p in (root / prefix).rglob("SKILL.md")]
        paths += [p.relative_to(root).as_posix() for p in (root / "docs/skills").glob("*.md")]
        read = lambda path: (root / path).read_text(encoding="utf-8")
    skills = sorted({p for p in paths if p.endswith("/SKILL.md") and p.startswith(SKILL_ROOTS)})
    errors = []
    if not skills:
        return ["no skills found"]
    for path in skills:
        try:
            meta, body = skill_document(read(path))
            name = require_text(meta, ("name",))
            if name != Path(path).parent.name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
                raise ValueError("name must match its directory and use lowercase words separated by hyphens")
            require_text(meta, ("description",))
            disabled = meta.get(("disable-model-invocation",), False)
            if type(disabled) is not bool:
                raise ValueError("disable-model-invocation must be a boolean")
            if path.startswith(".claude/skills/"):
                source = ".agents/skills/{}/SKILL.md".format(name)
                if source not in skills:
                    raise ValueError("wrapper is missing its shared source: " + source)
                source_meta, _ = skill_document(read(source))
                if meta != source_meta:
                    raise ValueError("wrapper metadata must match " + source)
                expected = "Read and follow `{}` from this repository's root.".format(source)
                if body != expected:
                    raise ValueError("wrapper body must contain only: " + expected)
                # The shared source owns Codex UI metadata.
                continue
            if path.startswith(".agents/skills/"):
                wrapper = ".claude/skills/{}/SKILL.md".format(name)
                if wrapper not in skills:
                    raise ValueError("shared skill is missing its Claude wrapper: " + wrapper)
            ui = mapping(read(str(Path(path).parent.as_posix()) + "/agents/openai.yaml"))
            require_text(ui, ("interface", "display_name"))
            description = require_text(ui, ("interface", "short_description"))
            if not 25 <= len(description) <= 64:
                raise ValueError("short_description must contain 25–64 characters")
            implicit = ui.get(("policy", "allow_implicit_invocation"), True)
            if type(implicit) is not bool or implicit == disabled:
                raise ValueError("allow_implicit_invocation must be the opposite of disable-model-invocation")
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            errors.append("{}: {}".format(path, error))
    for path in sorted(p for p in paths if p.startswith("docs/skills/") and p.endswith(".md")):
        try:
            intent_docs.parse(read(path))
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            errors.append("{}: {}".format(path, error))
    return errors


def staged_tooling_changed(root):
    # Disable rename detection so moves out of these directories still trigger tests.
    paths = git(root, "diff", "--cached", "--name-only", "--no-renames", "-z").decode().split("\0")
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
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip())
    errors = check(root, args.staged)
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
