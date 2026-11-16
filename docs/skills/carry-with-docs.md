# Carry With Docs

An agent-led design interview that develops a glossary and records consequential design decisions.

## Invocation

Follow the explicit user-invoked pattern in `AGENTS.md`: keep a human-facing description and enforce explicit-only selection with `disable-model-invocation: true` and `policy.allow_implicit_invocation: false`, matching `guide-with-docs`, since this workflow writes documentation files.

## Upstream

### Sources

[guide-with-docs](../../skills/guide-with-docs/SKILL.md).

### Desired differences

- Use the name `carry-with-docs`, a description naming the agent-led interview, the display name "Carry With Docs", and a short description that settles rather than guides decisions.
- Compose `carry-me` with `domain-modeling`, replacing the `guide-me` dependency. This carries Carry Me's stronger default, deciding even consequential choices unless a wrong guess about the user's goals would be costly, into the documented interview.
- During the interview, apply `domain-modeling` in conversation only; write its glossary updates and decision records once the user confirms the shared understanding. Carry Me settles most decisions without the user, so recording as the interview goes would write documentation the user has not reviewed. `domain-modeling` still challenges terms, sharpens wording, and cross-references the code during the interview; only the writing waits. If the session ends before confirmation, nothing is recorded.

### Inherited behavior to preserve

- Before starting the interview, check that both dependencies can be loaded. Show the install command for each missing dependency, then stop, without substituting another workflow or installing automatically.
- Apply both dependencies together with an agent-neutral instruction: `carry-me` handles the interview; `domain-modeling` develops the glossary and records consequential design decisions once the user confirms.
- Keep `domain-modeling` as a separately installed, model-callable dependency with its supporting files.
- Keep this skill a small composition entry point. The dependencies own their detailed workflows; Carry Me's interview and final-confirmation requirements still apply.

### Diff

Compared with the working-tree [`guide-with-docs`](../../skills/guide-with-docs/SKILL.md) files. Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is kept current by the pre-commit check.

#### SKILL.md

````diff
--- upstream/skills/guide-with-docs/SKILL.md
+++ skills/carry-with-docs/SKILL.md
@@ -1,14 +1,16 @@
 ---
-name: guide-with-docs
-description: A guided design interview that also develops the glossary and records consequential design decisions.
+name: carry-with-docs
+description: An agent-led design interview that also develops the glossary and records consequential design decisions.
 disable-model-invocation: true
 ---
 
-Before starting the interview, check that both the "guide-me" and "domain-modeling" skills can be loaded. If either is unavailable, show the install command for each missing one, then stop:
+Before starting the interview, check that both the "carry-me" and "domain-modeling" skills can be loaded. If either is unavailable, show the install command for each missing one, then stop:
 
-- "guide-me": `npx skills add adammansfield/my-skills --skill guide-me`
+- "carry-me": `npx skills add adammansfield/my-skills --skill carry-me`
 - "domain-modeling": `npx skills add mattpocock/skills --skill domain-modeling`
 
 Leave setup to the user: do not substitute another workflow or install skills automatically.
 
 Once both dependencies are available, load and apply them together.
+
+During the interview, apply "domain-modeling" in conversation only; write its glossary updates and decision records once the user confirms the shared understanding.
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
