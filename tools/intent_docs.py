"""Parse and validate intent docs (docs/skills/*.md). Python 3.8+, standard library only.

An intent doc has one `# Skill Name` title, a description, one `## Invocation`
section, and, for an adapted skill, one `## Upstream` section whose `### Sources`
names one upstream SKILL.md. An external upstream is a GitHub repository, and its
`### Diff` names one baseline commit in that repository. An in-repo upstream is a
skill in this repository, linked as `../../skills/NAME/SKILL.md`, and its `### Diff`
compares against the current files instead of a commit.
"""

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import Optional, Tuple


GITHUB = r"https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9._-]+"
EXTERNAL = re.compile(r"(" + GITHUB + r")/blob/[^/\s)]+/([^\s)]+/SKILL\.md)")
IN_REPO = re.compile(r"\]\(\.\./\.\./(skills/[^/\s)]+)/SKILL\.md\)")


@dataclass(frozen=True)
class Section:
    level: int
    title: str
    start: int
    body_start: int
    end: int


@dataclass(frozen=True)
class Upstream:
    """An adapted skill's source. `repo` and `baseline` are None for an in-repo upstream."""
    repo: Optional[str]
    source: str
    baseline: Optional[str]
    diff: Section

    @property
    def skill(self):
        """The upstream skill's name: the last part of its source path."""
        return PurePosixPath(self.source).name


@dataclass(frozen=True)
class IntentDoc:
    text: str
    sections: Tuple[Section, ...]
    upstream: Optional[Upstream]

    def body(self, title, level=2):
        section = _one(self.sections, level, title)
        return self.text[section.body_start:section.end]


def parse(text):
    """Return an IntentDoc, or raise ValueError naming the first contract violation."""
    sections = _sections(text)
    titles = [s for s in sections if s.level == 1]
    if len(titles) != 1 or text[:titles[0].start].strip():
        raise ValueError("start with exactly one # Skill Name heading")
    following = sections[1].start if len(sections) > 1 else len(text)
    if not text[titles[0].body_start:following].strip():
        raise ValueError("include a description between the title and first section")
    _one(sections, 2, "Invocation")
    upstream = [s for s in sections if (s.level, s.title) == (2, "Upstream")]
    if not upstream:
        if EXTERNAL.search(_prose(text)):
            raise ValueError("intent docs that link an upstream skill require ## Upstream")
        return IntentDoc(text, sections, None)
    return IntentDoc(text, sections, _upstream(text, sections, _one(sections, 2, "Upstream")))


def declares_upstream(text):
    """Return whether the text has a `## Upstream` heading outside fenced blocks, without validating it."""
    return any((s.level, s.title) == (2, "Upstream") for s in _sections(text))


def with_diff(doc, target, patches):
    """Return the doc's text with its Diff section rebuilt.

    `target` is the upstream commit for an external upstream and None for an in-repo
    upstream. `patches` is a sequence of (filename, unified diff) pairs.
    """
    upstream = doc.upstream
    if upstream.repo:
        compared = "Compared with [upstream commit `{}`]({}/commit/{}).".format(target[:12], upstream.repo, target)
        refreshed = "is refreshed during syncing"
    else:
        compared = "Compared with the working-tree [`{0}`](../../skills/{0}/SKILL.md) files.".format(upstream.skill)
        refreshed = "is kept current by the pre-commit check"
    content = ("### Diff\n\n{} Minus lines are upstream; plus lines are local. The sections above define "
               "intended behavior; this snapshot records the implementation and {}.\n").format(compared, refreshed)
    for filename, delta in patches:
        fence = "`" * max(4, max((len(run) + 1 for run in re.findall(r"`+", delta)), default=4))
        content += "\n#### {}\n\n{}diff\n{}{}\n".format(filename, fence, delta, fence)
    diff = doc.upstream.diff
    if diff.end < len(doc.text):
        content += "\n"
    newline = "\r\n" if "\r\n" in doc.text else "\n"
    return doc.text[:diff.start] + content.replace("\n", newline) + doc.text[diff.end:]


def _upstream(text, sections, upstream):
    children = [s for s in sections if upstream.start < s.start < upstream.end]
    if not children or children[0].level != 3:
        raise ValueError("organize ## Upstream with ### subsections")
    sources = _one(children, 3, "Sources")
    diff = _one(children, 3, "Diff")
    body = text[sources.body_start:sources.end]
    external, local = EXTERNAL.findall(body), IN_REPO.findall(body)
    if len(external) + len(local) != 1:
        raise ValueError("Sources must contain one unambiguous upstream SKILL.md link")
    if local:
        return Upstream(None, local[0], None, diff)
    repo, path = external[0]
    source = PurePosixPath(path).parent
    if source.is_absolute() or ".." in source.parts:
        raise ValueError("invalid upstream source path")
    attribution = _prose(text[diff.body_start:diff.end])
    baselines = set(re.findall(re.escape(repo) + r"/commit/([0-9a-f]{40})(?![0-9a-f])", attribution))
    if len(baselines) != 1:
        raise ValueError("Diff must identify one full upstream baseline SHA")
    return Upstream(repo, str(source), baselines.pop(), diff)


def _one(sections, level, title):
    matches = [s for s in sections if (s.level, s.title) == (level, title)]
    if len(matches) != 1:
        raise ValueError("expected exactly one {} {} section".format("#" * level, title))
    return matches[0]


def _sections(text):
    headings = []
    for line, offset in _prose_lines(text):
        match = re.match(r"^ {0,3}(#{1,6}) +(.+?)\s*#*\s*$", line)
        if match:
            headings.append((len(match[1]), match[2], offset, offset + len(line)))
    return tuple(
        Section(level, title, start, body_start,
                next((h[2] for h in headings if h[2] > start and h[0] <= level), len(text)))
        for level, title, start, body_start in headings)


def _prose(text):
    return "".join(line for line, _ in _prose_lines(text))


def _prose_lines(text):
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
