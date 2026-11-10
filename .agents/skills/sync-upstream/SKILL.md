---
name: sync-upstream
description: Sync this repository's adapted skills with Matt Pocock's upstream while preserving local principles.
disable-model-invocation: true
metadata:
  internal: true
---

Work in the `adammansfield/my-skills` checkout. Read its root `AGENTS.md` and the relevant intent documents before comparing upstream:

- [Guide Me](../../../docs/skills/guide-me.md)
- [Guide With Docs](../../../docs/skills/guide-with-docs.md)

These documents define the source mappings, deliberate differences, and inherited behavior to preserve.

1. Inspect local changes before editing. Preserve unrelated work and distinguish it from this sync in the final diff.
2. Fetch upstream into a temporary directory, or use connected GitHub tools. Resolve one upstream commit and use it for every file in this comparison. Read the mapped sources and relevant invocation guidance. Follow renames when paths move.
3. Compare each upstream source with its local adaptation and inspect upstream history for the changes being considered. If an existing upstream-diff snapshot or previous sync commit records an upstream SHA, compare that baseline with the target as well. Keep upstream improvements distinct from intentional local differences; do not infer ancestry solely from similar text.
4. Apply the smallest changes that satisfy the intent documents. Keep unchanged upstream wording where it fits, and avoid unrelated refactors, invocation changes, or extra documentation. Ask about upstream changes that conflict with the documented intent instead of silently weakening it or rewriting the requirements to match upstream. Keep licensing notices current if upstream notices change.
5. Refresh the affected documents' `## Upstream` → `### Diff` sections using the same resolved upstream commit and the final local `SKILL.md` and `agents/openai.yaml`. Record the commit link and generate unified diffs with upstream as the old side and local as the new side, under `####` file headings. These snapshots record implementation differences; the desired-difference and inherited-behavior sections remain the requirements. Run `python3 tools/check_skills.py` (or `python` on Windows). Inspect the resulting diff against every requirement in each affected intent document, including inherited behavior and dependency composition. Distinguish metadata validation from behavioral assessment and report any unverified behavior.
6. Report the upstream SHA, adopted and skipped changes with reasons, remaining intentional differences, and validation results. Include that SHA in a sync commit's body when a commit is requested, so the next sync can find its baseline. Commit, push, or reinstall only when requested.

Use Git and the available tools for comparison. If a reusable helper becomes necessary, implement it in cross-platform Python using only the standard library.
