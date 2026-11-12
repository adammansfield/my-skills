# Guide With Docs

A guided design interview that develops a glossary and records consequential architecture decisions.

## Invocation

Follow the explicit user-invoked pattern in `AGENTS.md`: keep a human-facing description and enforce explicit-only selection with `disable-model-invocation: true` and `policy.allow_implicit_invocation: false`.

## Upstream

### Sources

[grill-with-docs](https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md).

### Desired differences

- Use the name `guide-with-docs` and compose `guiding` with `domain-modeling`, replacing upstream's `grilling` dependency with the guided variant. This carries Guiding's automatic-decision behavior into the documented interview.
- Use an agent-neutral instruction to load and apply both dependencies, so the workflow works in Codex and Claude Code without naming a host-specific tool.
- If `guiding` is unavailable, show `npx skills add adammansfield/my-skills --skill '*'` and stop. Ask for setup rather than substituting another interview or installing automatically.
- Before starting the interview, check that both dependencies can be loaded. If `domain-modeling` is unavailable, show `npx skills add mattpocock/skills --skill domain-modeling` and stop, without substituting another workflow or installing automatically. Its freshness remains managed by the separate dependency installation.

### Inherited behavior to preserve

- Apply both dependencies together: `guiding` handles the interview; `domain-modeling` develops the glossary and records consequential architecture decisions.
- Keep `domain-modeling` as a separately installed, model-callable dependency with its supporting files.
- Keep this skill a small composition entry point. The dependencies own their detailed workflows; Guiding's interview and final-confirmation requirements still apply.

### Diff

Compared with [upstream commit `5863806dd4e1`](https://github.com/mattpocock/skills/commit/5863806dd4e15c63174bee4e7515a4256792ecfa). Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is refreshed during syncing.

#### SKILL.md

````diff
--- upstream/skills/engineering/grill-with-docs/SKILL.md
+++ skills/guide-with-docs/SKILL.md
@@ -1,7 +1,13 @@
 ---
-name: grill-with-docs
-description: A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go.
+name: guide-with-docs
+description: A guided design interview that also develops the glossary and records consequential design decisions.
 disable-model-invocation: true
 ---
 
-Call the Skill tool twice, for "grilling" and "domain-modeling".
+Before starting the interview, check that both the "guiding" and "domain-modeling" skills can be loaded.
+
+If "guiding" is unavailable, show `npx skills add adammansfield/my-skills --skill '*'` and stop. Do not substitute another interview workflow or install skills automatically.
+
+If "domain-modeling" is unavailable, show `npx skills add mattpocock/skills --skill domain-modeling` and stop. Do not substitute another documentation workflow or install skills automatically.
+
+Once both dependencies are available, load and apply them together.
````

#### agents/openai.yaml

````diff
--- upstream/skills/engineering/grill-with-docs/agents/openai.yaml
+++ skills/guide-with-docs/agents/openai.yaml
@@ -1,5 +1,5 @@
 interface:
-  display_name: "Grill with Docs"
-  short_description: "Grill a design and write its docs"
+  display_name: "Guide With Docs"
+  short_description: "Guide design decisions and document the domain model"
 policy:
   allow_implicit_invocation: false
````
