# Guide Me

A guided design interview that makes reasonable decisions by default and asks when missing goals or priorities could change a consequential choice, working like a tour guide: it handles the route and asks you to choose at the forks that matter.

## Invocation

Follow the implicit user-invoked pattern in `AGENTS.md`, with the description `Use when the user requests "guide me", not "guide me through" a task.` Keep model invocation enabled so the natural-language phrase, including a spoken "Guide me?" opener, can select the skill, and so `guide-with-docs` can load it by name. The exclusion keeps the common request for step-by-step instructions from starting an interview for users who never meant to invoke it.

## Upstream

### Sources

[grilling](https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md).

### Desired differences

- Use the name `guide-me`, the description quoted in `## Invocation`, the display name "Guide Me", and the short description "Work through design decisions with a guided interview".
  - _Why:_ ordinary task matching should not select this variant without the phrase.
- Hold the interview in this skill rather than in a separate workflow skill.
  - _Why:_ upstream splits it into explicit-only `grill-me`, which only calls `grilling`, because its commands may not call other commands. Here `guide-me` stays model-callable, so `guide-with-docs` loads it directly, as `AGENTS.md` allows for skills called by other skills.
- Replace the opening sentence "Interview the user relentlessly until you reach a shared understanding." with "Question the design relentlessly until you and the user reach a shared understanding."
  - _Why:_ questioning stays relentless but targets the design rather than the user; the decision paragraph decides who answers each question. Upstream's "Interview the user" pulls toward asking, against deciding by default.
- Add this decision paragraph right after the opening paragraph:
  > Make reasonable decisions on the user's behalf by default. Summarize automatic decisions, their reasons, and meaningful tradeoffs. Ask when missing information about the user's goals or priorities could materially change a consequential decision. Consequential decisions substantially affect people, outcomes, resources, or future options. Consider downstream effects and the difficulty or cost of changing course.
  - _Why:_ deciding by default is inherent to the workflow, so it needs no sign of indifference or delegation phrase from the user; asking is reserved for consequential decisions that depend on goals the user has not shared.
- Remove the last sentence of the paragraph starting "Finding _facts_", "The _decisions_ are the user's: put each to them and wait."
  - _Why:_ it contradicts deciding by default.
- Add a label paragraph right after the decision paragraph: present automatic decisions as bullets labeled **A**, **B**, …, **Z**, **AA**, **AB**, …, skipping any label containing Q; continue the sequence across rounds and retain each decision's label throughout the thread.
  - _Why:_ letters distinguish objections to decisions from answers to numbered questions while preserving upstream question formatting.
  - _Why:_ skipping Q keeps a terse reply such as "Q no" from being mistaken for a reference to `Q1`, `Q2`, and so on.
- In the paragraph starting "Work the tree in **rounds**", between the frontier definition and the instruction to ask the frontier, add "Resolve automatic decisions, recompute the frontier, and continue through newly unblocked automatic decisions.", and change "Ask the whole frontier" to "Ask the whole remaining frontier".
  - _Why:_ automatic decisions unblock others, so a round asks only what is left after deciding everything it can.
- Replace "Format a round like so:" with "A round can look like this; annotations, grouping, and ordering may vary as needed:", and start the example with these automatic decision bullets, each beginning with 🟢 inside the bullet, and a separator before the first question. Name the emoji only in the example, as with ❓ and ➡️:
  ```
  - 🟢 **A** - **<decision title>.** <summary of the automatic decision, its reasons and any meaningful tradeoffs>.
  - 🟢 **B** - **<decision title>.** <summary of the automatic decision, its reasons and any meaningful tradeoffs>.

  ---
  ```
  - _Why:_ rounds keep the example's general shape of decisions before questions, but may annotate, group, or reorder where that conveys a quicker understanding. This flexibility does not change the final recap's ordering.
  - _Why:_ the green 🟢 marks a settled decision apart from the red ❓ of an open question at a glance, and reads as "going ahead" rather than as approval the user has not yet given.
  - _Why:_ inside a bullet, long decisions wrap aligned with their text rather than under the marker.
- Replace the opening "Each round the user answers reshapes the tree" with "Each round of user answers and automatic decisions reshapes the tree", and right after its first sentence add: when the user overturns a decision, revisit the decisions that depended on it, keep their labels, and say which changed.
  - _Why:_ automatic decisions settle prerequisites just as answers do, so they also push the frontier outward.
  - _Why:_ revisiting dependants means later decisions never rest on a rejected one.
- In the paragraph starting "The session is done", right before "Do not act on it", add: before asking for confirmation, list every decision still in effect by label, leading with those that are hard to reverse or that you made with low confidence.
  - _Why:_ review lands where it matters, and the record survives long threads.

### Inherited behavior to preserve

- Organize the interview as a design tree and work through its frontier in rounds. Dependent questions wait until their prerequisites are settled.
- Ask the whole unresolved frontier together, using upstream question formatting and recommendations, and keep `Word each question so "yes" accepts your recommended answer.` right after the example.
- Find each environmental fact through a sub-agent with a fresh context window rather than asking the user to look it up. Keep unrelated questions moving while exploration runs.
- Finish only when the frontier is empty and the user confirms the shared understanding. Automatic decisions do not replace that final confirmation or authorize implementation.

### Diff

Compared with [upstream commit `5863806dd4e1`](https://github.com/mattpocock/skills/commit/5863806dd4e15c63174bee4e7515a4256792ecfa). Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is refreshed during syncing.

#### SKILL.md

````diff
--- upstream/skills/productivity/grilling/SKILL.md
+++ skills/guide-me/SKILL.md
@@ -1,15 +1,24 @@
 ---
-name: grilling
-description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
+name: guide-me
+description: Use when the user requests "guide me", not "guide me through" a task.
 ---
 
-Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.
+Question the design relentlessly until you and the user reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.
 
-Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.
+Make reasonable decisions on the user's behalf by default. Summarize automatic decisions, their reasons, and meaningful tradeoffs. Ask when missing information about the user's goals or priorities could materially change a consequential decision. Consequential decisions substantially affect people, outcomes, resources, or future options. Consider downstream effects and the difficulty or cost of changing course.
 
-Format a round like so:
+Present automatic decisions as bullets labeled **A**, **B**, …, **Z**, **AA**, **AB**, …, skipping any label containing Q; continue the sequence across rounds and retain each decision's label throughout the thread.
+
+Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Resolve automatic decisions, recompute the frontier, and continue through newly unblocked automatic decisions. Ask the whole remaining frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.
+
+A round can look like this; annotations, grouping, and ordering may vary as needed:
 
 ```
+- 🟢 **A** - **<decision title>.** <summary of the automatic decision, its reasons and any meaningful tradeoffs>.
+- 🟢 **B** - **<decision title>.** <summary of the automatic decision, its reasons and any meaningful tradeoffs>.
+
+---
+
 ❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>
 
 ➡️ <your recommended answer>
@@ -23,8 +32,8 @@
 
 Word each question so "yes" accepts your recommended answer.
 
-Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.
+Each round of user answers and automatic decisions reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. When the user overturns a decision, revisit the decisions that depended on it, keep their labels, and say which changed. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.
 
-Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent with a fresh context window to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.
+Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent with a fresh context window to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now.
 
-The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.
+The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Before asking for confirmation, list every decision still in effect by label, leading with those that are hard to reverse or that you made with low confidence. Do not act on it until the user confirms you have reached a shared understanding.
````

#### agents/openai.yaml

````diff
--- upstream/skills/productivity/grilling/agents/openai.yaml
+++ skills/guide-me/agents/openai.yaml
@@ -1,3 +1,3 @@
 interface:
-  display_name: "Grilling"
-  short_description: "Stress-test thinking a round of questions at a time"
+  display_name: "Guide Me"
+  short_description: "Work through design decisions with a guided interview"
````
