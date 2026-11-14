# My skills

- **Guide Me** (`guide-me`): a guided design interview that makes reasonable decisions by default and asks when missing goals or priorities could change a consequential choice.
- **Guide With Docs** (`guide-with-docs`): Guide Me with glossary and architecture decision documentation. Requires Matt Pocock's separately installed [`domain-modeling`](https://github.com/mattpocock/skills) skill.
- **Carry Me** (`carry-me`): an agent-led design interview that accepts its own recommendations for nearly every decision and asks only when it cannot infer a goal and a wrong guess would be costly.

## Install

```sh
npx skills add adammansfield/my-skills --skill '*'
npx skills add mattpocock/skills --skill domain-modeling
```
