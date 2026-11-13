# Maintenance

- Keep `README.md` to a bullet list of skills and one install command.
- Keep skill instructions in `SKILL.md` and UI metadata in `agents/openai.yaml`.
- Keep licensing and attribution in the root `LICENSE` and `THIRD_PARTY_NOTICES.md`.
- Keep domain terms in `GLOSSARY.md`.
- Skill docs use `# {Skill Name}`, a one-sentence description, and `## Invocation`. Skills with an upstream also include `## Upstream`, organized with `###` subsections, including exactly one `### Sources` linking the upstream `SKILL.md` and one `### Diff` naming the baseline commit.

## Local checks

Enable the pre-commit hook once per checkout with `git config core.hooksPath .githooks`. It always checks staged skill metadata, Claude wrapper consistency, and intent-document structure. Staged changes under `tools/` or `.githooks/` also run the full working-tree Python test suite, including renames and deletions. Checks require dependency-free Python 3.8+. Run `python3 tools/check_skills.py --tests` to check working files and run all tests; omit `--tests` for metadata and doc checks alone. Use `python` if that is your Python 3 command. The hook only selects the interpreter and runs the checker; keep check logic in Python.

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

## Editing skills with an upstream

Before editing an upstream-backed skill, read its `docs/skills/NAME.md` for source mappings, deliberate differences, and inherited behavior to preserve. Update the documented differences when changing intended behavior.

After editing, regenerate the affected skill's `### Diff` section against its existing documented upstream baseline. Use an upstream Git checkout containing that commit:

```sh
python3 tools/upstream_snapshots.py --upstream-dir PATH --ref BASELINE_SHA --skill NAME --write
```

Keep the baseline unchanged for local edits; follow `sync-upstream` when adopting upstream changes. Run `python3 tools/check_skills.py` and review the resulting diff against the affected intent document.

## Syncing with upstream

At the start of a fresh session working in this repository, run `python3 tools/upstream_snapshots.py --status`. If the check is due (no successful check or at least 30 days old), follow `sync-upstream` in check mode, report relevant changes, and continue the requested work. This is best-effort agent behavior: if upstream is unavailable, continue without retrying during the session. Explicit check or sync requests always bypass the freshness interval.

When syncing upstream, read the docs for [Guiding](docs/skills/guiding.md), [Guide Me](docs/skills/guide-me.md), and [Guide With Docs](docs/skills/guide-with-docs.md) for source mappings, deliberate differences, and inherited behavior to preserve. Use the repository's [sync-upstream skill](.agents/skills/sync-upstream/SKILL.md) for the procedure. Keep any helper scripts in cross-platform Python using only the standard library.
