# Guide Me

A guided design interview that makes reasonable decisions by default and asks when missing goals or priorities could change a consequential choice, working like a tour guide: it handles the route and asks you to choose at the forks that matter.

## Invocation

Follow the implicit user-invoked pattern in `AGENTS.md`, with the description `Use when the user requests "guide me", not "guide me through" a task.` Keep model invocation enabled so the natural-language phrase, including a spoken "Guide me?" opener, can select the skill, and so `guide-with-docs` can load it by name. The exclusion keeps the common request for step-by-step instructions from starting an interview for users who never meant to invoke it. This deliberately differs from upstream's explicit-only `grill-me` entry point and its model-invoked `grilling` description.

## Upstream

### Sources

[grilling](https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md).

### Desired differences

- Use the name `guide-me`, its phrase-based description, the display name "Guide Me", and model-callable metadata. Ordinary task matching should not select this variant without the phrase.
- Hold the interview in this skill rather than in a separate workflow skill. Upstream splits it into explicit-only `grill-me`, which only calls `grilling`, because its commands may not call other commands. Here `guide-me` stays model-callable, so `guide-with-docs` loads it directly, as `AGENTS.md` allows for skills called by other skills.
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
+++ skills/guide-me/SKILL.md
@@ -1,11 +1,15 @@
 ---
-name: grilling
-description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
+name: guide-me
+description: Use when the user requests "guide me", not "guide me through" a task.
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
+++ skills/guide-me/agents/openai.yaml
@@ -1,3 +1,5 @@
 interface:
-  display_name: "Grilling"
-  short_description: "Stress-test thinking a round of questions at a time"
+  display_name: "Guide Me"
+  short_description: "Work through design decisions with a guided interview"
+policy:
+  allow_implicit_invocation: true
````
