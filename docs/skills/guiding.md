# Guiding

The shared guided design interview that makes reasonable decisions by default and asks when missing goals or priorities could change a consequential choice.

## Invocation

Follow the explicit model-invoked pattern in `AGENTS.md`. Keep this skill model-callable, with the description `Use only when called by the guide-me or guide-with-docs skill.` This confines intended selection to composition instead of competing with upstream `grilling` for ordinary user requests. The description is a routing convention, not an enforced caller whitelist; explicit user invocation remains possible.

## Upstream

### Sources

[grilling](https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md).

### Desired differences

- Use the name `guiding` and the caller-scoped description above. Both entry points share this workflow, keeping their adaptations small.
- Make reasonable decisions on the user's behalf by default, including choices with legitimate alternatives and tradeoffs. This authority is inherent to the workflow and does not require the user to express indifference or use a delegation phrase.
- Summarize automatically accepted decisions, their reasons, and meaningful tradeoffs. Recompute the frontier and continue through newly unblocked automatic decisions before asking the remaining questions.
- Label automatic decision bullets A–Z, then AA–AZ, BA–BZ, and onward, keeping labels unique and stable throughout the thread. Letters distinguish objections to decisions from numbered question answers while preserving upstream question formatting. Skip any label containing Q so a terse reply such as "Q no" cannot be mistaken for a reference to question `Q1`, `Q2`, and so on.
- Ask when missing information about the user's goals or priorities could materially change a consequential decision, and wait for their answers. Consequential decisions substantially affect outcomes, the people involved, the resources required, or future options. Consider downstream effects and how difficult or costly it would be to change course.

### Inherited behavior to preserve

- Organize the interview as a design tree and work through its frontier in rounds. Dependent questions wait until their prerequisites are settled.
- Ask the whole unresolved frontier together, using upstream question formatting and recommendations that the user can accept with "yes".
- Find environmental facts through fresh-context sub-agents rather than asking the user to look them up. Keep unrelated questions moving while exploration runs.
- Finish only when the frontier is empty and the user confirms the shared understanding. Automatically accepted decisions do not replace that final confirmation or authorize implementation.

### Diff

Compared with [upstream commit `5863806dd4e1`](https://github.com/mattpocock/skills/commit/5863806dd4e15c63174bee4e7515a4256792ecfa). Minus lines are upstream; plus lines are local. The sections above define intended behavior; this snapshot records the implementation and is refreshed during syncing.

#### SKILL.md

````diff
--- upstream/skills/productivity/grilling/SKILL.md
+++ skills/guiding/SKILL.md
@@ -1,11 +1,15 @@
 ---
-name: grilling
-description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
+name: guiding
+description: Use only when called by the guide-me or guide-with-docs skill.
 ---
 
 Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.
 
-Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.
+Make reasonable decisions on the user's behalf by default. Summarize automatically accepted choices, their reasons, and meaningful tradeoffs. Ask when missing information about the user's goals or priorities could materially change a consequential decision. Consequential decisions substantially affect outcomes, the people involved, the resources required, or future options. Consider downstream effects and how difficult or costly it would be to change course.
+
+Present automatic decisions as bullets labeled **A**, **B**, …, **Z**, **AA**, **AB**, …, skipping any label containing Q; continue the sequence across rounds and retain each decision's label throughout the thread.
+
+Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Resolve automatic decisions, recompute the frontier, and continue through newly unblocked automatic decisions. Ask the whole remaining frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.
 
 Format a round like so:
 
@@ -23,8 +27,8 @@
 
 Word each question so "yes" accepts your recommended answer.
 
-Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.
+Each round of user answers and automatic decisions reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.
 
-Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent with a fresh context window to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.
+Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent with a fresh context window to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now.
 
 The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.
````

#### agents/openai.yaml

````diff
--- upstream/skills/productivity/grilling/agents/openai.yaml
+++ skills/guiding/agents/openai.yaml
@@ -1,3 +1,5 @@
 interface:
-  display_name: "Grilling"
-  short_description: "Stress-test thinking a round of questions at a time"
+  display_name: "Guiding"
+  short_description: "Run the shared guided design interview"
+policy:
+  allow_implicit_invocation: true
````
