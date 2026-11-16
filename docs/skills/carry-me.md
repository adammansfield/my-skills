# Carry Me

An agent-led design interview that accepts its own recommendations for nearly every decision and asks only when it cannot infer a goal and a wrong guess would be costly: where Guide Me leads the tour, Carry Me carries you, the way one player does the heavy lifting for a team, and you confirm on arrival.

## Invocation

Follow the implicit user-invoked pattern in `AGENTS.md`, with the description `Use when the user requests "carry me".` Keep model invocation enabled so the natural-language phrase can select the skill, matching `guide-me`, and so `carry-with-docs` can load it by name.

## Upstream

### Sources

[guide-me](../../skills/guide-me/SKILL.md).

### Desired differences

- Use the name `carry-me`, the description quoted in `## Invocation`, the display name "Carry Me", and the short description "Settle design decisions with an agent-led interview".
  - _Why:_ "carry me" is rarely an ordinary request, so the description needs no exclusion clause; ordinary task matching should not select this variant without the phrase.
- Replace Guide Me's decision paragraph with:
  > Decide on the user's behalf by default, accepting your recommended answer even for consequential decisions with legitimate alternatives. When in doubt, decide and say so. Summarize automatic decisions, their reasons, and meaningful tradeoffs. Ask only when a decision depends on the user's goals, values, or constraints that you cannot reasonably infer, and a wrong guess would be costly or hard to reverse. Consequential decisions substantially affect people, outcomes, resources, or future options.
  - _Why:_ Guide Me asks whenever missing information could materially change a consequential decision; Carry Me leans toward deciding.
  - _Why:_ it keeps Guide Me's definition of consequential decisions, which scopes both the stronger default and the second opinion, but drops "Consider downstream effects…", which would widen the ask rule.
- Add this paragraph right after the round paragraph, which starts "Work the tree in **rounds**":
  > Get a blind **second opinion** before building on or presenting the consequential automatic decisions you just made. Give them in one batch to a sub-agent with a fresh context window, along with the options you weighed, the user's known goals, and the settled decisions they build on, but not your choices; it may propose a better option. Keep the decisions where it picks your answer, and turn the rest into questions that show both answers and recommend the stronger one.
  - _Why:_ it restores some of the review the stronger default removes without asking the user about every consequential decision.
  - _Why:_ it is blind so the sub-agent's answer is not anchored on Carry Me's.
  - _Why:_ because it runs before anything builds on a decision, nothing rests on a disputed one, and a disputed decision appears only as a numbered question, never with a letter label.
  - _Why:_ sharing the options keeps it to one cheap sub-agent call per batch rather than a second exploration. Carry Me's framing may still steer the sub-agent; the invitation to propose another option catches some missed alternatives.

### Inherited behavior to preserve

- Keep every other part of `guide-me` identical.
- When a round has no questions, keep resolving in the same turn through the inherited "continue through newly unblocked automatic decisions", stopping only for a genuine question or the final confirmation.
  - _Why:_ under Carry Me's stronger default, a round often has no questions.
- Finish only when the frontier is empty and the user confirms the shared understanding. Automatic decisions do not authorize implementation.
  - _Why:_ with fewer questions, the final summary is the user's main checkpoint.

### Diff

Compared with the working-tree [`guide-me`](../../skills/guide-me/SKILL.md) files. Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is kept current by the pre-commit check.

#### SKILL.md

````diff
--- upstream/skills/guide-me/SKILL.md
+++ skills/carry-me/SKILL.md
@@ -1,15 +1,17 @@
 ---
-name: guide-me
-description: Use when the user requests "guide me", not "guide me through" a task.
+name: carry-me
+description: Use when the user requests "carry me".
 ---
 
 Question the design relentlessly until you and the user reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.
 
-Make reasonable decisions on the user's behalf by default. Summarize automatic decisions, their reasons, and meaningful tradeoffs. Ask when missing information about the user's goals or priorities could materially change a consequential decision. Consequential decisions substantially affect people, outcomes, resources, or future options. Consider downstream effects and the difficulty or cost of changing course.
+Decide on the user's behalf by default, accepting your recommended answer even for consequential decisions with legitimate alternatives. When in doubt, decide and say so. Summarize automatic decisions, their reasons, and meaningful tradeoffs. Ask only when a decision depends on the user's goals, values, or constraints that you cannot reasonably infer, and a wrong guess would be costly or hard to reverse. Consequential decisions substantially affect people, outcomes, resources, or future options.
 
 Present automatic decisions as bullets labeled **A**, **B**, …, **Z**, **AA**, **AB**, …, skipping any label containing Q; continue the sequence across rounds and retain each decision's label throughout the thread.
 
 Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Resolve automatic decisions, recompute the frontier, and continue through newly unblocked automatic decisions. Ask the whole remaining frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.
+
+Get a blind **second opinion** before building on or presenting the consequential automatic decisions you just made. Give them in one batch to a sub-agent with a fresh context window, along with the options you weighed, the user's known goals, and the settled decisions they build on, but not your choices; it may propose a better option. Keep the decisions where it picks your answer, and turn the rest into questions that show both answers and recommend the stronger one.
 
 A round can look like this; annotations, grouping, and ordering may vary as needed:
 
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
