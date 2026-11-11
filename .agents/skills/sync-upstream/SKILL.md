---
name: sync-upstream
description: Use when the user wants to check or sync this repository's adapted skills with Matt Pocock's upstream, or a session-entry freshness check is due.
metadata:
  internal: true
---

Work in the `adammansfield/my-skills` checkout. Read its root `AGENTS.md` and the relevant intent documents before comparing upstream:

- [Guiding](../../../docs/skills/guiding.md)
- [Guide Me](../../../docs/skills/guide-me.md)
- [Guide With Docs](../../../docs/skills/guide-with-docs.md)

These documents define the source mappings, deliberate differences, and inherited behavior to preserve.

## Mode

- **Check**: report relevant upstream changes without editing tracked files. Use this for "check upstream", session-entry checks, or an ambiguous request to see what changed.
- **Sync**: apply compatible local changes, refresh snapshots, and validate without another confirmation. Ask when upstream conflicts with documented intent. Commit, push, and reinstall only when the request includes those actions.

An explicit request always checks immediately. For a session-entry check, `python3 tools/upstream_snapshots.py --status` reports whether a check is due. If fresh, continue the user's task. If fetching fails, briefly report it and continue; leave the successful-check record unchanged and avoid repeated attempts that session.

## Comparison

1. Inspect local changes. Preserve unrelated work and distinguish it from any sync edits.
2. Fetch upstream into a temporary Git checkout containing the target and documented baseline commits. Resolve one target commit for the entire comparison. Read the mapped sources, relevant invocation guidance, and licensing notices. Follow renames when paths move; the helper reports missing files rather than guessing new mappings.
3. Run the snapshot helper in read-only mode:

   ```sh
   python3 tools/upstream_snapshots.py --upstream-dir PATH --ref REF
   ```

   It reads source mappings and baseline SHAs from the docs. Exit 0 means snapshots match, 1 means snapshots are stale, and 2 means a comparison error. `source_changed` distinguishes changes to mapped files from a newer target SHA alone; `snapshot_stale` also reflects local edits. A stale snapshot is not itself evidence of an upstream improvement. Use the reported baseline-to-target history and compare upstream with local intent before deciding what to adopt.
4. In check mode, report the target SHA, relevant upstream changes or no changes, and any comparison gaps. Use the successful-check record section below when eligible, then finish without changing snapshots or skill files.

## Apply a sync

1. Apply the smallest changes that satisfy the intent documents. Keep unchanged upstream wording where it fits, and avoid unrelated refactors or invocation changes. Surface conflicts with intent instead of rewriting requirements to match upstream. Preserve required copyright and permission notices.
2. Refresh the affected documents' `## Upstream` → `### Diff` sections:

   ```sh
   python3 tools/upstream_snapshots.py --upstream-dir PATH --ref SHA --write
   ```

   Use the resolved target SHA from the comparison. Repeat `--skill NAME` to limit affected skills. The helper preserves content outside the Diff sections. The prose defines intent; generated snapshots record implementation differences.
3. Run `python3 tools/check_skills.py` and inspect the resulting diff against every requirement in the affected intent documents, including inherited behavior and dependency composition. Distinguish metadata checks from behavioral assessment and report unverified behavior.
4. Report the upstream SHA, adopted and skipped changes with reasons, remaining intentional differences, and validation. Include that SHA in a sync commit's body when a commit is requested.

## Successful-check record

After a successful comparison of **all** adapted skills, record the resolved target SHA, even if it found changes:

```sh
python3 tools/upstream_snapshots.py --record-check SHA
```

This writes only checkout-local Git state, containing the UTC timestamp, upstream SHA, and comparison scope. Do not record a partial or failed check as a complete check. In check mode, record after reporting; in sync mode, record after the final snapshots and validation so the scope reflects the result.

Keep fetching, history review, and adoption decisions in the agent workflow. Helpers use cross-platform Python and only the standard library; use `python` where that is the Python 3 command.
