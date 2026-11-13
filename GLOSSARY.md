# My Skills

Agent skills maintained in this repository, some adapted from Matt Pocock's upstream skills.

## Language

**Intent doc**:
The document in `docs/skills/` that states what a skill is for, how it is invoked and, for an adapted skill, how it relates to upstream.
_Avoid_: skill doc, design doc

**Adapted skill**:
A skill derived from an upstream skill, identified by its intent doc's `## Upstream` section.
_Avoid_: upstream-backed skill, forked skill

**Baseline**:
The upstream commit an adapted skill was last compared with.
_Avoid_: base, upstream version

**Diff snapshot**:
The recorded difference between an adapted skill's upstream source at its baseline and the local skill.
_Avoid_: patch, diff section

**Check record**:
The checkout-local note of when every adapted skill was last compared with upstream, and at which upstream commit.
_Avoid_: freshness state, sync log
