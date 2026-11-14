---
name: link-skills
description: Use when the user requests "link skills" or wants this checkout's skills installed for local agents, including after adding, renaming, or removing a skill.
metadata:
  internal: true
---

From this repository's root, run:

```sh
python3 .agents/skills/link-skills/scripts/link_skills.py
```

It links each `skills/NAME` from `~/.agents/skills/NAME`, then links that from the Claude Code skills folder (`$CLAUDE_CONFIG_DIR/skills`, else `~/.claude/skills`), so edits in this checkout are live without reinstalling. Each run also removes links left by renamed or removed skills. Add `--dry-run` to preview, and repeat `--agent-dir PATH` to link into other agents' skills folders instead.

A real folder, such as a copy from `npx skills add`, or a link to elsewhere is left in place and reported, with exit status 1. Show the user what it found and ask before removing it, then rerun.

Report the links made and removed. Use `python` where that is the Python 3 command.
