# Guide Me

A phrase-triggered entry point for the shared guided design interview, which works like a tour guide: it handles the route and asks you to choose at the forks that matter.

## Invocation

Follow the implicit user-invoked pattern in `AGENTS.md`, with the description `Use when the user requests "guide me", not "guide me through" a task.` Keep model invocation enabled so the natural-language phrase, including a spoken "Guide me?" opener, can select the skill. The exclusion keeps the common request for step-by-step instructions from starting an interview for users who never meant to invoke it. This deliberately differs from upstream's explicit-only entry point.

## Upstream

### Sources

[grill-me](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md).

### Desired differences

- Use the name `guide-me`, its phrase-based description, and model-callable metadata. Ordinary task matching should not select this variant without the phrase, and "guide me through" a task asks for instructions rather than an interview.
- Load and apply `guiding` instead of upstream `grilling`, using an agent-neutral instruction.
- If `guiding` is unavailable, show `npx skills add adammansfield/my-skills --skill '*'` and stop. Preserve the intended workflow by asking for setup rather than substituting another interview or installing automatically.

### Inherited behavior to preserve

- Keep this skill a thin entry point. The shared interview and its final-confirmation requirement belong to `guiding`; avoid duplicating the interview here.

### Diff

Compared with [upstream commit `5863806dd4e1`](https://github.com/mattpocock/skills/commit/5863806dd4e15c63174bee4e7515a4256792ecfa). Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is refreshed during syncing.

#### SKILL.md

````diff
--- upstream/skills/productivity/grill-me/SKILL.md
+++ skills/guide-me/SKILL.md
@@ -1,7 +1,8 @@
 ---
-name: grill-me
-description: A relentless interview to sharpen a plan or design.
-disable-model-invocation: true
+name: guide-me
+description: Use when the user requests "guide me", not "guide me through" a task.
 ---
 
-Call the Skill tool with "grilling".
+Load and apply the "guiding" skill.
+
+If "guiding" is unavailable, show `npx skills add adammansfield/my-skills --skill '*'` and stop. Do not substitute another interview workflow or install skills automatically.
````

#### agents/openai.yaml

````diff
--- upstream/skills/productivity/grill-me/agents/openai.yaml
+++ skills/guide-me/agents/openai.yaml
@@ -1,5 +1,5 @@
 interface:
-  display_name: "Grill Me"
-  short_description: "Sharpen a plan through interview"
+  display_name: "Guide Me"
+  short_description: "Work through design decisions with a guided interview"
 policy:
-  allow_implicit_invocation: false
+  allow_implicit_invocation: true
````
