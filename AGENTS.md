# Maintenance

- Keep `README.md` to a bullet list of skills and install commands.
- Keep skill instructions in `SKILL.md` and UI metadata in `agents/openai.yaml`.
- Keep licensing and attribution in the root `LICENSE` and `THIRD_PARTY_NOTICES.md`. Add an attribution before adopting a skill from a new external upstream.
- Keep domain terms in `GLOSSARY.md`.
- Intent docs (`docs/skills/NAME.md`) use `# {Skill Name}`, a one-sentence description, and `## Invocation`. Adapted skills also include `## Upstream`, organized with `###` subsections, including exactly one `### Sources` linking the upstream `SKILL.md` and one `### Diff`. An external upstream is a GitHub repository: link its `SKILL.md` by URL, and `### Diff` names the baseline commit there. An in-repo upstream is another skill here: link it as `../../skills/NAME/SKILL.md`, and `### Diff` compares against its working-tree files.

## Local checks

Enable the pre-commit hook once per checkout with `git config core.hooksPath .githooks`. It always checks staged skill metadata, Claude wrapper consistency, intent-document structure, that each skill has one intent doc and a README bullet, that a description quoted in `## Invocation` matches the skill's, and that each in-repo adaptation's `### Diff` matches its source's staged files. Staged changes under `tools/` or `.githooks/`, or to any Python file, also run the full working-tree Python test suite, including renames and deletions. Checks require dependency-free Python 3.8+. Run `python3 tools/check_skills.py --tests` to check working files and run all tests; omit `--tests` for metadata and doc checks alone. Use `python` if that is your Python 3 command. The hook only selects the interpreter and runs the checker; keep check logic in Python.

## Invocation

These are authoring patterns; description-based matching is a convention, not an enforced boundary.

| Pattern | Description |
|---|---|
| Explicit user-invoked | A human-facing summary; metadata requires explicit invocation. |
| Implicit user-invoked | `Use when the user requests "trigger phrase".` |
| Implicit user- and model-invoked | `Use when the user requests "trigger phrase" or wants to <task>.` |
| Implicit model-invoked | `Use when the user wants to <task>.` |
| Explicit model-invoked | `Use only when called by the <caller> skill.` |

- When a trigger phrase has a common everyday meaning, an implicit pattern may add `, not "<phrase>" <context>` to exclude it, as in `Use when the user requests "show me", not "show me how" to do a task.` The exclusion is a matching hint, not enforcement.
- Explicit user-only skills set `disable-model-invocation: true` in `SKILL.md` and `policy.allow_implicit_invocation: false` in `agents/openai.yaml`.
- The other patterns remain model-callable and can still be invoked explicitly.
- Skills called by other skills must remain model-callable. Name dependencies in the caller's instructions; list callers in a dependency's description when expressing a restricted calling convention. Explicit model invocation means the caller names the skill, not that metadata enforces a caller whitelist.

## Editing skills with an upstream

Before editing an adapted skill, read its `docs/skills/NAME.md` for source mappings, deliberate differences, and inherited behavior to preserve. Update the documented differences when changing intended behavior.

After editing, regenerate the affected skill's `### Diff` section. For an external upstream, compare against its existing documented baseline, using an upstream Git checkout containing that commit:

```sh
python3 tools/upstream_snapshots.py --upstream URL --upstream-dir PATH --ref BASELINE_SHA --skill NAME --write
```

Keep the baseline unchanged for local edits; follow `sync-upstream` when adopting upstream changes.

For an in-repo upstream, regenerate against the working tree:

```sh
python3 tools/upstream_snapshots.py --in-repo --write
```

Editing a skill that others adapt in-repo makes their snapshots stale. In the same commit, adapt those skills to the change as their intent docs require, then regenerate their snapshots; the pre-commit check rejects stale ones. Run `python3 tools/check_skills.py` and review the resulting diff against the affected intent document.

## Syncing with upstream

At the start of a fresh session working in this repository, run `python3 tools/upstream_snapshots.py --status`. For each external upstream whose check is due (no successful check or at least 30 days old), follow `sync-upstream` in check mode, report relevant changes, and continue the requested work. In-repo upstreams are never due; the pre-commit check keeps them current. If `--status` fails, report its error and continue the requested work without checking upstream. This is best-effort agent behavior: if upstream is unavailable, continue without retrying during the session. Explicit check or sync requests always bypass the freshness interval.

When syncing upstream, read the intent doc of every adapted skill (each `docs/skills/*.md` with `## Upstream`; `--status` lists them under `skills`) for source mappings, deliberate differences, and inherited behavior to preserve. Use the repository's [sync-upstream skill](.agents/skills/sync-upstream/SKILL.md) for the procedure. Keep any helper scripts in cross-platform Python using only the standard library.
