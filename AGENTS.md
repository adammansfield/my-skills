# Maintenance

- Keep `README.md` to a bullet list of skills and one install command.
- Keep skill instructions in `SKILL.md` and UI metadata in `agents/openai.yaml`.
- Keep licensing and attribution in the root `LICENSE` and `THIRD_PARTY_NOTICES.md`.
- Skill docs use `# {Skill Name}`, a one-sentence description, and `## Invocation`. Skills with an upstream also include `## Upstream`, organized with `###` subsections.

## Local checks

Enable the pre-commit hook once per checkout with `git config core.hooksPath .githooks`. It checks staged skill metadata and Claude wrapper consistency using dependency-free Python 3.8+. Run `python3 tools/check_skills.py` to check working files; use `python` if that is your Python 3 command. The hook only selects the interpreter and runs the checker; keep check logic in Python.

## Invocation

These are authoring patterns; description-based matching is a convention, not an enforced boundary.

| Pattern | Description |
|---|---|
| Explicit user-invoked | A human-facing summary; metadata requires explicit invocation. |
| Implicit user-invoked | `Use when the user requests "trigger phrase".` |
| Implicit user- and model-invoked | `Use when the user requests "trigger phrase" or wants to <task>.` |
| Implicit model-invoked | `Use when the user wants to <task>.` |
| Explicit model-invoked | `Use only when called by the <caller> skill.` |

- Explicit user-only skills set `disable-model-invocation: true` in `SKILL.md` and `policy.allow_implicit_invocation: false` in `agents/openai.yaml`.
- The other patterns remain model-callable and can still be invoked explicitly.
- Skills called by other skills must remain model-callable. Name dependencies in the caller's instructions; list callers in a dependency's description when expressing a restricted calling convention. Explicit model invocation means the caller names the skill, not that metadata enforces a caller whitelist.

## Syncing with upstream

When syncing upstream, read the docs for [Guiding](docs/skills/guiding.md), [Guide Me](docs/skills/guide-me.md), and [Guide With Docs](docs/skills/guide-with-docs.md) for source mappings, deliberate differences, and inherited behavior to preserve. Use the repository's [sync-upstream skill](.agents/skills/sync-upstream/SKILL.md) for the procedure. Keep any helper scripts in cross-platform Python using only the standard library.
