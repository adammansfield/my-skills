# Guide Me

A phrase-triggered entry point for the shared guided design interview.

## Invocation

Follow the implicit user-invoked pattern in `AGENTS.md`, with the description `Use when the user requests "guide me".` Keep model invocation enabled so the natural-language phrase can select the skill. This deliberately differs from upstream's explicit-only entry point.

## Upstream

### Sources

[grill-me](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md).

### Desired differences

- Use the name `guide-me`, its phrase-based description, and model-callable metadata. Ordinary task matching should not select this variant without the phrase.
- Load and apply `guiding` instead of upstream `grilling`, using an agent-neutral instruction.
- If `guiding` is unavailable, show `npx skills add adammansfield/my-skills --skill '*'` and stop. Preserve the intended workflow by asking for setup rather than substituting another interview or installing automatically.

### Inherited behavior to preserve

- Keep this skill a thin entry point. The shared interview and its final-confirmation requirement belong to `guiding`; avoid duplicating the interview here.

### Diff

Compared with [upstream commit `4ae2317ddb22`](https://github.com/mattpocock/skills/commit/4ae2317ddb22b046e26455e4f9c9b3aaaf62212d). Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is refreshed during syncing.

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
+description: Use when the user requests "guide me".
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
