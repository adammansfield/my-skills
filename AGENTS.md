# Maintenance

- Keep `README.md` to a bullet list of skills and one install command.
- Keep skill instructions in `SKILL.md` and UI metadata in `agents/openai.yaml`.
- Keep licensing and attribution in the root `LICENSE` and `THIRD_PARTY_NOTICES.md`.

## Local checks

Enable the pre-commit hook once per checkout with `git config core.hooksPath .githooks`. It checks staged skill metadata and Claude wrapper consistency using dependency-free Python 3.8+. Run `python3 tools/check_skills.py` to check working files; use `python` if that is your Python 3 command. The hook only selects the interpreter and runs the checker; keep check logic in Python.

## Invocation

These are authoring patterns; description-based matching is a convention, not an enforced boundary.

| Pattern | Description |
|---|---|
| Explicit user-invoked | A human-facing summary; metadata requires explicit invocation. |
| Implicit user-invoked | `Use when the user requests "trigger phrase".` |
| Implicit user- and model-invoked | `Use when the user requests "trigger phrase" or wants to <task>.` |
| Model-invoked | `Use when the user wants to <task>.` |

- Explicit-only skills set `disable-model-invocation: true` in `SKILL.md` and `policy.allow_implicit_invocation: false` in `agents/openai.yaml`.
- The other patterns remain model-callable and can still be invoked explicitly.
- Skills called by other skills must remain model-callable. Name dependencies in the caller's instructions; dependency descriptions need not list their callers.

## Syncing with upstream

- Preserve Guide Me's automatic decisions when one option clearly dominates against the user's goals and verified constraints, explanations of those decisions, and final shared-understanding confirmation before implementation.
- Preserve Guide With Docs' composition with `guide-me` and the separately installed `domain-modeling` skill.
- Review changes from [Matt Pocock's skills](https://github.com/mattpocock/skills) selectively, preserving this repository's deliberate differences.
