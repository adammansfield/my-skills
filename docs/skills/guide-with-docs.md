# Guide With Docs

A guided design interview that develops a glossary and records consequential design decisions.

## Invocation

Follow the explicit user-invoked pattern in `AGENTS.md`: keep a human-facing description and enforce explicit-only selection with `disable-model-invocation: true` and `policy.allow_implicit_invocation: false`.

## Upstream

### Sources

[grill-with-docs](https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md).

### Desired differences

- Use the name `guide-with-docs`, the description "A guided design interview that also develops the glossary and records consequential design decisions.", the display name "Guide With Docs", and the short description "Guide design decisions and document the domain model".
  - _Why:_ Guide Me decides by default instead of questioning the user on every choice, so upstream's relentless interview no longer describes it.
- Compose `guide-me` with `domain-modeling`, replacing upstream's `grilling` dependency.
  - _Why:_ this carries Guide Me's automatic-decision behavior into the documented interview.
- Replace upstream's body, "Call the Skill tool twice, for "grilling" and "domain-modeling".", with:
  ```
  Before starting the interview, check that both the "guide-me" and "domain-modeling" skills can be loaded. If either is unavailable, show the install command for each missing one, then stop:

  - "guide-me": `npx skills add adammansfield/my-skills --skill guide-me`
  - "domain-modeling": `npx skills add mattpocock/skills --skill domain-modeling`

  Leave setup to the user: do not substitute another workflow or install skills automatically.

  Once both dependencies are available, load and apply them together.
  ```
  - _Why:_ "load and apply them together" is agent-neutral, so the workflow works in Codex and Claude Code without naming a host-specific tool.
  - _Why:_ checking first shows every missing install command at once, and the user stays in control of setup. `domain-modeling`'s freshness stays managed by its separate installation.

### Inherited behavior to preserve

- Apply both dependencies together: `guide-me` handles the interview; `domain-modeling` develops the glossary and records consequential design decisions.
- Let `domain-modeling` update the glossary and record decisions as the interview settles them, as upstream does.
- Keep `domain-modeling` as a separately installed, model-callable dependency with its supporting files.
- Keep this skill a small composition entry point, with no workflow beyond the dependency check and loading.
  - _Why:_ the dependencies own their detailed workflows; Guide Me's interview and final-confirmation requirements still apply.

### Diff

Compared with [upstream commit `5863806dd4e1`](https://github.com/mattpocock/skills/commit/5863806dd4e15c63174bee4e7515a4256792ecfa). Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is refreshed during syncing.

#### SKILL.md

````diff
--- upstream/skills/engineering/grill-with-docs/SKILL.md
+++ skills/guide-with-docs/SKILL.md
@@ -1,7 +1,14 @@
 ---
-name: grill-with-docs
-description: A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go.
+name: guide-with-docs
+description: A guided design interview that also develops the glossary and records consequential design decisions.
 disable-model-invocation: true
 ---
 
-Call the Skill tool twice, for "grilling" and "domain-modeling".
+Before starting the interview, check that both the "guide-me" and "domain-modeling" skills can be loaded. If either is unavailable, show the install command for each missing one, then stop:
+
+- "guide-me": `npx skills add adammansfield/my-skills --skill guide-me`
+- "domain-modeling": `npx skills add mattpocock/skills --skill domain-modeling`
+
+Leave setup to the user: do not substitute another workflow or install skills automatically.
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
