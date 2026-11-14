# Carry With Docs

An agent-led design interview that develops a glossary and records consequential architecture decisions.

## Invocation

Follow the explicit user-invoked pattern in `AGENTS.md`: keep a human-facing description and enforce explicit-only selection with `disable-model-invocation: true` and `policy.allow_implicit_invocation: false`, matching `guide-with-docs`, since this workflow writes documentation files.

## Upstream

### Sources

[guide-with-docs](../../skills/guide-with-docs/SKILL.md).

### Desired differences

- Use the name `carry-with-docs`, a description naming the agent-led interview, the display name "Carry With Docs", and a short description that settles rather than guides decisions.
- Compose `carry-me` with `domain-modeling`, replacing the `guide-me` dependency. This carries Carry Me's stronger default, deciding even consequential choices unless a wrong guess about the user's goals would be costly, into the documented interview.
- Let `domain-modeling` record decisions Carry Me makes automatically under its own criteria, as it does for Guide Me's, rather than deferring documentation until the final confirmation.

### Inherited behavior to preserve

- Before starting the interview, check that both dependencies can be loaded. Show the install command for only the missing dependency and stop, without substituting another workflow or installing automatically.
- Apply both dependencies together with an agent-neutral instruction: `carry-me` handles the interview; `domain-modeling` develops the glossary and records consequential architecture decisions.
- Keep `domain-modeling` as a separately installed, model-callable dependency with its supporting files.
- Keep this skill a small composition entry point. The dependencies own their detailed workflows; Carry Me's interview and final-confirmation requirements still apply.

### Diff

Compared with the working-tree [`guide-with-docs`](../../skills/guide-with-docs/SKILL.md) files. Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is kept current by the pre-commit check.

#### SKILL.md

````diff
--- upstream/skills/guide-with-docs/SKILL.md
+++ skills/carry-with-docs/SKILL.md
@@ -1,12 +1,12 @@
 ---
-name: guide-with-docs
-description: A guided design interview that also develops the glossary and records consequential design decisions.
+name: carry-with-docs
+description: An agent-led design interview that also develops the glossary and records consequential design decisions.
 disable-model-invocation: true
 ---
 
-Before starting the interview, check that both the "guide-me" and "domain-modeling" skills can be loaded.
+Before starting the interview, check that both the "carry-me" and "domain-modeling" skills can be loaded.
 
-If "guide-me" is unavailable, show `npx skills add adammansfield/my-skills --skill guide-me` and stop. Do not substitute another interview workflow or install skills automatically.
+If "carry-me" is unavailable, show `npx skills add adammansfield/my-skills --skill carry-me` and stop. Do not substitute another interview workflow or install skills automatically.
 
 If "domain-modeling" is unavailable, show `npx skills add mattpocock/skills --skill domain-modeling` and stop. Do not substitute another documentation workflow or install skills automatically.
 
````

#### agents/openai.yaml

````diff
--- upstream/skills/guide-with-docs/agents/openai.yaml
+++ skills/carry-with-docs/agents/openai.yaml
@@ -1,5 +1,5 @@
 interface:
-  display_name: "Guide With Docs"
-  short_description: "Guide design decisions and document the domain model"
+  display_name: "Carry With Docs"
+  short_description: "Settle design decisions and document the domain model"
 policy:
   allow_implicit_invocation: false
````
