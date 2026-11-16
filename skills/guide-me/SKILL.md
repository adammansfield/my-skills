---
name: guide-me
description: Use when the user requests "guide me", not "guide me through" a task.
---

Question the design relentlessly until you and the user reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Make reasonable decisions on the user's behalf by default. Summarize automatic decisions, their reasons, and meaningful tradeoffs. Ask when missing information about the user's goals or priorities could materially change a consequential decision. Consequential decisions substantially affect people, outcomes, resources, or future options. Consider downstream effects and the difficulty or cost of changing course.

Present automatic decisions as bullets labeled **A**, **B**, …, **Z**, **AA**, **AB**, …, skipping any label containing Q; continue the sequence across rounds and retain each decision's label throughout the thread.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Resolve automatic decisions, recompute the frontier, and continue through newly unblocked automatic decisions. Ask the whole remaining frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Word each question so "yes" accepts your recommended answer.

A round can look like this; annotations, grouping, and ordering may vary as needed:

```
- **A** - **<decision title>.** <summary of the automatic decision, its reasons and any meaningful tradeoffs>.
- **B** - **<decision title>.** <summary of the automatic decision, its reasons and any meaningful tradeoffs>.

---

❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Each round of user answers and automatic decisions reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. When the user overturns a decision, revisit the decisions that depended on it, keep their labels, and say which changed. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent with a fresh context window to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Before asking for confirmation, list every decision still in effect by label, leading with those that are hard to reverse or that you made with low confidence. Do not act on it until the user confirms you have reached a shared understanding.
