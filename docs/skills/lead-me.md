# Lead Me

A phrase-triggered entry point for the shared agent-led design interview.

## Invocation

Follow the implicit user-invoked pattern in `AGENTS.md`, with the description `Use when the user requests "lead me".` Keep model invocation enabled so the natural-language phrase can select the skill, matching `guide-me`.

## Upstream

### Sources

[guide-me](../../skills/guide-me/SKILL.md).

### Desired differences

- Use the name `lead-me`, its phrase-based description without Guide Me's "not 'guide me through'" exclusion (the phrase has no common competing meaning), and the display name "Lead Me" with an agent-led short description. Ordinary task matching should not select this variant without the phrase.
- Load and apply `leading` instead of `guiding`.
- If `leading` is unavailable, show `npx skills add adammansfield/my-skills --skill '*'` and stop, without substituting another interview or installing automatically.

### Inherited behavior to preserve

- Keep this skill a thin entry point. The shared interview and its final-confirmation requirement belong to `leading`; avoid duplicating the interview here.

### Diff

Compared with the working-tree [`guide-me`](../../skills/guide-me/SKILL.md) files. Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is kept current by the pre-commit check.

#### SKILL.md

````diff
--- upstream/skills/guide-me/SKILL.md
+++ skills/lead-me/SKILL.md
@@ -1,8 +1,8 @@
 ---
-name: guide-me
-description: Use when the user requests "guide me", not "guide me through" a task.
+name: lead-me
+description: Use when the user requests "lead me".
 ---
 
-Load and apply the "guiding" skill.
+Load and apply the "leading" skill.
 
-If "guiding" is unavailable, show `npx skills add adammansfield/my-skills --skill '*'` and stop. Do not substitute another interview workflow or install skills automatically.
+If "leading" is unavailable, show `npx skills add adammansfield/my-skills --skill '*'` and stop. Do not substitute another interview workflow or install skills automatically.
````

#### agents/openai.yaml

````diff
--- upstream/skills/guide-me/agents/openai.yaml
+++ skills/lead-me/agents/openai.yaml
@@ -1,5 +1,5 @@
 interface:
-  display_name: "Guide Me"
-  short_description: "Work through design decisions with a guided interview"
+  display_name: "Lead Me"
+  short_description: "Settle design decisions with an agent-led interview"
 policy:
   allow_implicit_invocation: true
````
