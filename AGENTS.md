# Maintenance

- Keep `README.md` to a bullet list of skills and one install command.
- Keep skill instructions in `SKILL.md` and UI metadata in `agents/openai.yaml`.
- Keep invocation settings consistent: user-only skills use `disable-model-invocation: true` in `SKILL.md` and `allow_implicit_invocation: false` in `agents/openai.yaml`. Skills called by other skills must remain model-callable.
- Keep licensing and attribution in the root `LICENSE` and `THIRD_PARTY_NOTICES.md`.

## Syncing with upstream

- Preserve Guide Me's automatic decisions when one option clearly dominates against the user's goals and verified constraints, explanations of those decisions, and final shared-understanding confirmation before implementation.
- Preserve Guide With Docs' composition with `guide-me` and the separately installed `domain-modeling` skill.
- Review changes from [Matt Pocock's skills](https://github.com/mattpocock/skills) selectively, preserving this repository's deliberate differences.
