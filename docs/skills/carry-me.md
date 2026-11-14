# Carry Me

An agent-led design interview that accepts its own recommendations for nearly every decision and asks only when it cannot infer a goal and a wrong guess would be costly: where Guide Me leads the tour, Carry Me carries you, as in the gaming slang for doing the heavy lifting, and you confirm on arrival.

## Invocation

Follow the implicit user-invoked pattern in `AGENTS.md`, with the description `Use when the user requests "carry me".` Keep model invocation enabled so the natural-language phrase can select the skill, matching `guide-me`.

## Upstream

### Sources

[guide-me](../../skills/guide-me/SKILL.md).

### Desired differences

- Use the name `carry-me`, its phrase-based description without an exclusion clause, since "carry me" is rarely an ordinary request, and the display name "Carry Me" with an agent-led short description. Ordinary task matching should not select this variant without the phrase.
- Replace Guide Me's decision paragraph with a stronger default: accept the recommended answer even for consequential decisions with legitimate alternatives, and when in doubt, decide and say so. Ask only when a decision depends on goals, values, or constraints that cannot reasonably be inferred **and** a wrong guess would be costly or hard to reverse. Guide Me asks whenever missing information could materially change a consequential decision; Carry Me leans toward deciding.
- Summarize each decision, its reason, and meaningful tradeoffs so the user can overturn it by label.

### Inherited behavior to preserve

- Keep every other part of `guide-me` identical: the design tree, rounds and frontier, lettered decision labels that skip Q, continuing through newly unblocked automatic decisions, question formatting with "yes" accepting the recommendation, and fresh-context sub-agents for environmental facts.
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
 
 Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.
 
-Make reasonable decisions on the user's behalf by default. Summarize automatically accepted choices, their reasons, and meaningful tradeoffs. Ask when missing information about the user's goals or priorities could materially change a consequential decision. Consequential decisions substantially affect outcomes, the people involved, the resources required, or future options. Consider downstream effects and how difficult or costly it would be to change course.
+Decide on the user's behalf by default, accepting your recommended answer even for consequential decisions with legitimate alternatives. When in doubt, decide and say so. Summarize each decision, its reason, and meaningful tradeoffs so the user can overturn it by label. Ask only when a decision depends on the user's goals, values, or constraints that you cannot reasonably infer, and a wrong guess would be costly or hard to reverse.
 
 Present automatic decisions as bullets labeled **A**, **B**, …, **Z**, **AA**, **AB**, …, skipping any label containing Q; continue the sequence across rounds and retain each decision's label throughout the thread.
 
````

#### agents/openai.yaml

````diff
--- upstream/skills/guide-me/agents/openai.yaml
+++ skills/carry-me/agents/openai.yaml
@@ -1,5 +1,5 @@
 interface:
-  display_name: "Guide Me"
-  short_description: "Work through design decisions with a guided interview"
+  display_name: "Carry Me"
+  short_description: "Settle design decisions with an agent-led interview"
 policy:
   allow_implicit_invocation: true
````
