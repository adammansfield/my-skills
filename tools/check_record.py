"""Decide when each external upstream's check is due, from Check records. Python 3.8+, standard library only.

A Check record notes when an external upstream's adapted skills were last compared with it, at
which upstream commit, and over which scope (skill names, sources and baselines). A check is due
30 days after its record, when the scope changes, or when the record is missing or malformed.
`status` and `record` are pure; `load` and `save` keep records in the checkout's Git directory.
"""

from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re

import repo


FRESH_FOR = timedelta(days=30)
SHA = re.compile(r"[0-9a-f]{40}")


def status(adapted, records, now):
    """Report whether each external upstream's check is due.

    `adapted` are the adapted skills (catalog.Doc values); `records` maps upstream URL to its record.
    In-repo adaptations are listed but never due: the pre-commit check keeps them current.
    """
    upstreams = [_status(url, items, records.get(url), now) for url, items in sorted(_external(adapted).items())]
    return dict(due=any(u["due"] for u in upstreams), upstreams=upstreams,
                in_repo=[a.name for a in adapted if a.upstream.repo is None], skills=[a.name for a in adapted])


def record(adapted, records, url, sha, now):
    """Return `records` with a completed check of every skill adapted from the external upstream `url`."""
    if not SHA.fullmatch(sha):
        raise ValueError("record a full upstream commit SHA")
    items = _external(adapted).get(url)
    if not items:
        raise ValueError("no skills are adapted from " + str(url))
    return dict(records, **{url: dict(checked_at=now.isoformat(), upstream_sha=sha, scope=_fingerprint(items))})


def path(root):
    """The checkout-local file that holds the records; Git neither tracks nor shares it."""
    location = Path(repo.git(root, "rev-parse", "--git-path", "upstream-check.json").strip())
    return location if location.is_absolute() else Path(root) / location


def load(root):
    """Return the stored records; an unreadable or malformed file holds none."""
    try:
        records = json.loads(path(root).read_bytes().decode("utf-8"))["upstreams"]
        return records if isinstance(records, dict) else {}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def save(root, records):
    repo.atomic_write(path(root), json.dumps(dict(upstreams=records), indent=2) + "\n")


def _external(adapted):
    """Map each external upstream URL to the adapted skills it supplies."""
    groups = {}
    for item in adapted:
        if item.upstream.repo:
            groups.setdefault(item.upstream.repo, []).append(item)
    return groups


def _fingerprint(items):
    scope = [(a.name, a.upstream.source, a.upstream.baseline) for a in items]
    return hashlib.sha256(json.dumps(scope).encode()).hexdigest()


def _status(url, items, entry, now):
    skills = [a.name for a in items]
    try:
        checked = datetime.fromisoformat(entry["checked_at"])
        if checked.tzinfo is None or checked > now or not SHA.fullmatch(entry["upstream_sha"]):
            raise ValueError("invalid check record")
        due = now - checked >= FRESH_FOR or entry["scope"] != _fingerprint(items)
        return dict(url=url, due=due, checked_at=entry["checked_at"], upstream_sha=entry["upstream_sha"], skills=skills)
    except (ValueError, KeyError, TypeError):
        return dict(url=url, due=True, checked_at=None, upstream_sha=None, skills=skills)
