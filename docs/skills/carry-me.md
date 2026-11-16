# Carry Me

An agent-led design interview that accepts its own recommendations for nearly every decision and asks only when it cannot infer a goal and a wrong guess would be costly: where Guide Me leads the tour, Carry Me carries you, the way one player does the heavy lifting for a team, and you confirm on arrival.

## Invocation

Follow the implicit user-invoked pattern in `AGENTS.md`, with the description `Use when the user requests "carry me".` Keep model invocation enabled so the natural-language phrase can select the skill, matching `guide-me`, and so `carry-with-docs` can load it by name.

## Upstream

### Sources

[guide-me](../../skills/guide-me/SKILL.md).

### Desired differences

- Use the name `carry-me`, its phrase-based description without an exclusion clause, since "carry me" is rarely an ordinary request, and the display name "Carry Me" with an agent-led short description. Ordinary task matching should not select this variant without the phrase.
- Replace Guide Me's decision paragraph with a stronger default: accept the recommended answer even for consequential decisions with legitimate alternatives, and when in doubt, decide and say so. Ask only when a decision depends on goals, values, or constraints that cannot reasonably be inferred **and** a wrong guess would be costly or hard to reverse. Guide Me asks whenever missing information could materially change a consequential decision; Carry Me leans toward deciding. Keep Guide Me's definition of consequential decisions, which scopes both the stronger default and the independent check, but drop its instruction to consider downstream effects, which would widen the ask rule.
- Before presenting each round, have a fresh-context sub-agent pick an answer for each of the round's consequential automatic decisions, given the options Carry Me weighed but not its choice, the user's known goals, and the settled decisions each builds on. It may propose a better option. Keep decisions where it picks Carry Me's answer, and turn the rest into questions that show both answers. The check restores some of the review the stronger default removes without asking the user about every consequential decision. Sharing the options keeps it to one cheap sub-agent call per round rather than a second exploration; Carry Me's framing may still steer the sub-agent, and the invitation to propose another option catches some missed alternatives.

### Inherited behavior to preserve

- Keep every other part of `guide-me` identical.
- Under Carry Me's stronger default, a round often has no questions: keep resolving in the same turn and stop only for a genuine question or the final confirmation.
- Finish only when the frontier is empty and the user confirms the shared understanding. Automatic decisions do not authorize implementation; with fewer questions, the final summary is the user's main checkpoint.

### Diff

Compared with the working-tree [`guide-me`](../../skills/guide-me/SKILL.md) files. Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is kept current by the pre-commit check.

#### SKILL.md

````diff
--- upstream/skills/guide-me/SKILL.md
+++ skills/carry-me/SKILL.md
@@ -1,11 +1,11 @@
 ---
-name: guide-me
-description: Use when the user requests "guide me", not "guide me through" a task.
+name: carry-me
+description: Use when the user requests "carry me".
 ---
 
 Question the design relentlessly until you and the user reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.
 
-Make reasonable decisions on the user's behalf by default. Summarize automatic decisions, their reasons, and meaningful tradeoffs. Ask when missing information about the user's goals or priorities could materially change a consequential decision. Consequential decisions substantially affect people, outcomes, resources, or future options. Consider downstream effects and the difficulty or cost of changing course.
+Decide on the user's behalf by default, accepting your recommended answer even for consequential decisions with legitimate alternatives. When in doubt, decide and say so. Summarize automatic decisions, their reasons, and meaningful tradeoffs. Ask only when a decision depends on the user's goals, values, or constraints that you cannot reasonably infer, and a wrong guess would be costly or hard to reverse. Consequential decisions substantially affect people, outcomes, resources, or future options. Before presenting each round, give a fresh-context sub-agent each of the round's consequential automatic decisions with the options you weighed but not your choice, plus the user's known goals and the settled decisions it builds on; it may propose a better option. Keep the decisions where it picks your answer, and ask the user about the rest, showing both answers.
 
 Present automatic decisions as bullets labeled **A**, **B**, …, **Z**, **AA**, **AB**, …, skipping any label containing Q; continue the sequence across rounds and retain each decision's label throughout the thread.
 
````

#### agents/openai.yaml

````diff
--- upstream/skills/guide-me/agents/openai.yaml
+++ skills/carry-me/agents/openai.yaml
@@ -1,3 +1,3 @@
 interface:
-  display_name: "Guide Me"
-  short_description: "Work through design decisions with a guided interview"
+  display_name: "Carry Me"
+  short_description: "Settle design decisions with an agent-led interview"
````
