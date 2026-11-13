# My Skills

Agent skills maintained in this repository, some adapted from upstream skills.

## Language

**Intent doc**:
The document in `docs/skills/` that states what a skill is for, how it is invoked and, for an adapted skill, how it relates to upstream.
_Avoid_: skill doc, design doc

**Upstream**:
Where an adapted skill comes from: an external GitHub repository, compared at a baseline commit, or an in-repo skill, compared with its current files.
_Avoid_: origin, parent skill

**Adapted skill**:
A skill derived from an upstream skill, identified by its intent doc's `## Upstream` section.
_Avoid_: upstream-backed skill, forked skill

**In-repo adaptation**:
An adapted skill whose upstream is another skill in this repository.
_Avoid_: local fork, derived skill

**Baseline**:
The external upstream commit an adapted skill was last compared with. In-repo upstreams have none.
_Avoid_: base, upstream version

**Diff snapshot**:
The recorded difference between an adapted skill's upstream source and the local skill. An external upstream's source is read at its baseline; an in-repo upstream's source is read from the working tree, or from staged files in the pre-commit check.
_Avoid_: patch, diff section

**Check record**:
The checkout-local note of when each external upstream's adapted skills were last compared with it, and at which upstream commit.
_Avoid_: freshness state, sync log

**Shared skill**:
A repository-maintenance skill kept in `.agents/skills/` for every agent that works in this repository.
_Avoid_: internal skill, agents skill

**Claude wrapper**:
The copy of a shared skill in `.claude/skills/` that repeats its frontmatter and points Claude Code to it.
_Avoid_: Claude copy, shim
