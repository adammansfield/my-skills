# Leading

The shared agent-led design interview that accepts its own recommendations for nearly every decision and asks only when it cannot infer a goal and a wrong guess would be costly.

## Invocation

Follow the explicit model-invoked pattern in `AGENTS.md`. Keep this skill model-callable, with the description `Use only when called by the lead-me skill.` This confines intended selection to composition instead of competing with `guiding` or upstream `grilling` for ordinary user requests. The description is a routing convention, not an enforced caller whitelist; explicit user invocation remains possible.

## Upstream

### Sources

[guiding](../../skills/guiding/SKILL.md).

### Desired differences

- Use the name `leading`, the caller-scoped description above, and the display name "Leading" with an agent-led short description.
- Replace Guiding's decision paragraph with a stronger default: accept the recommended answer even for consequential decisions with legitimate alternatives, and when in doubt, decide and say so. Ask only when a decision depends on goals, values, or constraints that cannot reasonably be inferred **and** a wrong guess would be costly or hard to reverse. Guiding asks whenever missing information could materially change a consequential decision; Leading leans toward deciding.
- Summarize each decision, its reason, and meaningful tradeoffs so the user can overturn it by its label.

### Inherited behavior to preserve

- Keep every other part of `guiding` identical: the design tree, rounds and frontier, lettered decision labels that skip Q, continuing through newly unblocked automatic decisions, question formatting with "yes" accepting the recommendation, and fresh-context sub-agents for environmental facts.
- Continue through newly unblocked automatic decisions before asking. Under Leading's stronger default, this often leaves a round with no questions: keep resolving in the same turn and stop only for a genuine question or the final confirmation.
- Finish only when the frontier is empty and the user confirms the shared understanding. Automatic decisions do not authorize implementation; with fewer questions, the final summary is the user's main checkpoint.

### Diff

Compared with the working-tree [`guiding`](../../skills/guiding/SKILL.md) files. Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is kept current by the pre-commit check.

#### SKILL.md

````diff
--- upstream/skills/guiding/SKILL.md
+++ skills/leading/SKILL.md
@@ -1,11 +1,11 @@
 ---
-name: guiding
-description: Use only when called by the guide-me or guide-with-docs skill.
+name: leading
+description: Use only when called by the lead-me skill.
 ---
 
 Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.
 
-Make reasonable decisions on the user's behalf by default. Summarize automatically accepted choices, their reasons, and meaningful tradeoffs. Ask when missing information about the user's goals or priorities could materially change a consequential decision. Consequential decisions substantially affect outcomes, the people involved, the resources required, or future options. Consider downstream effects and how difficult or costly it would be to change course.
+Decide on the user's behalf by default, accepting your recommended answer even for consequential decisions with legitimate alternatives. When in doubt, decide and say so. Summarize each decision, its reason, and meaningful tradeoffs so the user can overturn it by label. Ask only when a decision depends on the user's goals, values, or constraints that you cannot reasonably infer, and a wrong guess would be costly or hard to reverse.
 
 Present automatic decisions as bullets labeled **A**, **B**, …, **Z**, **AA**, **AB**, …, skipping any label containing Q; continue the sequence across rounds and retain each decision's label throughout the thread.
 
````

#### agents/openai.yaml

````diff
--- upstream/skills/guiding/agents/openai.yaml
+++ skills/leading/agents/openai.yaml
@@ -1,5 +1,5 @@
 interface:
-  display_name: "Guiding"
-  short_description: "Run the shared guided design interview"
+  display_name: "Leading"
+  short_description: "Run the shared agent-led design interview"
 policy:
   allow_implicit_invocation: true
````
