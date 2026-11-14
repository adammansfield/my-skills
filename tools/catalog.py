"""Read every skill, internal skill, Claude wrapper and intent doc in a tree once. Python 3.8+, standard library only.

`read(tree)` never raises for one bad file: a file that cannot be read or parsed becomes a
problem on its own path, and the entry it belongs to carries None for what failed. Rules
that need a parsed value skip entries without one, since the catalog already reported why.

Frontmatter and `agents/openai.yaml` use the repository's YAML subset: space-indented
mappings and single-line scalars. This is a metadata reader, not a general-purpose YAML parser.
"""

from dataclasses import dataclass, field
import json
from pathlib import PurePosixPath
import re
from typing import Dict, List, Optional, Tuple

import intent_docs


SKILLS, INTERNAL, WRAPPERS = "skills/", ".agents/skills/", ".claude/skills/"
ROOTS = (SKILLS, INTERNAL, WRAPPERS)
FILES = ("SKILL.md", "agents/openai.yaml")  # A skill's files, relative to its directory.
DOCS = re.compile(r"docs/skills/[^/]+\.md")  # Intent docs.


def skill_path(root, name, filename="SKILL.md"):
    return "{}{}/{}".format(root, name, filename)


def doc_path(name):
    return "docs/skills/{}.md".format(name)


@dataclass(frozen=True)
class Skill:
    """A skill under SKILLS or INTERNAL. `fields`, `frontmatter` and `ui` are None when unreadable."""
    name: str
    path: str
    fields: Optional[Dict[Tuple[str, ...], object]]
    frontmatter: Optional[str]  # The raw block, delimiters and original newlines included.
    ui: Optional[Dict[Tuple[str, ...], object]]


@dataclass(frozen=True)
class Wrapper:
    """A Claude wrapper. `text` is None when unreadable."""
    name: str
    path: str
    text: Optional[str]


@dataclass(frozen=True)
class Doc:
    """An intent doc. `doc` is None when it fails to parse; `adapted` says whether it declares ## Upstream."""
    name: str
    path: str
    doc: Optional[intent_docs.IntentDoc]
    adapted: bool

    @property
    def upstream(self):
        return self.doc.upstream if self.doc else None


@dataclass(frozen=True)
class Catalog:
    skills: Dict[str, Skill]
    internal: Dict[str, Skill]
    wrappers: Dict[str, Wrapper]
    docs: Dict[str, Doc]
    problems: List[Tuple[str, str]] = field(default_factory=list)

    def adaptations(self):
        """The adapted skills whose intent docs parsed, by name."""
        return [d for _, d in sorted(self.docs.items()) if d.upstream]

    def problem(self, path):
        return next((message for p, message in self.problems if p == path), None)


def read(tree):
    """Return the Catalog of `tree` (see repo)."""
    problems = []
    groups = {root: {} for root in ROOTS}
    docs = {}
    paths = tree.paths()
    for path in paths:
        if path.endswith("/SKILL.md") and path.startswith(ROOTS):
            root = next(r for r in ROOTS if path.startswith(r))
            if path[len(root):].count("/") != 1:
                problems.append((path, "skills must be at {}NAME/SKILL.md".format(root)))
            else:
                groups[root][PurePosixPath(path).parent.name] = path
        elif DOCS.fullmatch(path):
            docs[PurePosixPath(path).stem] = _doc(tree, path, problems)
    paths = set(paths)
    return Catalog(
        skills={name: _skill(tree, paths, SKILLS, name, problems) for name in sorted(groups[SKILLS])},
        internal={name: _skill(tree, paths, INTERNAL, name, problems) for name in sorted(groups[INTERNAL])},
        wrappers={name: Wrapper(name, path, _read(tree, path, problems))
                  for name, path in sorted(groups[WRAPPERS].items())},
        docs=docs, problems=problems)


def _read(tree, path, problems):
    try:
        return tree.read(path)
    except (OSError, ValueError) as error:
        problems.append((path, str(error)))
        return None


def _skill(tree, paths, root, name, problems):
    path, ui_path = skill_path(root, name), skill_path(root, name, "agents/openai.yaml")
    fields = frontmatter = ui = None
    text = _read(tree, path, problems)
    if text is not None:
        try:
            frontmatter, fields = split_frontmatter(text)
        except ValueError as error:
            problems.append((path, str(error)))
    if ui_path not in paths:
        problems.append((path, "missing " + ui_path))
    else:
        text = _read(tree, ui_path, problems)
        try:
            ui = None if text is None else mapping(text)
        except ValueError as error:
            problems.append((ui_path, str(error)))
    return Skill(name, path, fields, frontmatter, ui)


def _doc(tree, path, problems):
    text = _read(tree, path, problems)
    if text is None:
        return Doc(PurePosixPath(path).stem, path, None, False)
    try:
        parsed = intent_docs.parse(text)
    except ValueError as error:
        problems.append((path, str(error)))
        parsed = None
    return Doc(PurePosixPath(path).stem, path, parsed, intent_docs.declares_upstream(text))


def split_frontmatter(text):
    """Return (raw frontmatter block, fields) for a document that starts with `---` frontmatter."""
    lines = text.splitlines(keepends=True)
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip("\r\n") == "---"), None)
    if not lines or lines[0].rstrip("\r\n") != "---" or end is None:
        raise ValueError("missing YAML frontmatter delimiters")
    return "".join(lines[:end + 1]), mapping("".join(lines[1:end]))


def mapping(text):
    """Parse the YAML subset into {key path tuple: value}; a key with nested keys maps to None."""
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
