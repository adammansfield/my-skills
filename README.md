# My skills

- **Guide Me** (`guide-me`): a guided design interview that makes reasonable decisions by default and asks when missing goals or priorities could change a consequential choice.
- **Guide With Docs** (`guide-with-docs`): Guiding with glossary and architecture decision documentation. Requires Matt Pocock's separately installed [`domain-modeling`](https://github.com/mattpocock/skills) skill.
- **Guiding** (`guiding`): the shared interview workflow required by Guide Me and Guide With Docs.
- **Lead Me** (`lead-me`): an agent-led design interview that accepts its own recommendations for nearly every decision and asks only when it cannot infer a goal and a wrong guess would be costly.
- **Leading** (`leading`): the shared interview workflow required by Lead Me.

## Install

```sh
npx skills add adammansfield/my-skills --skill '*'
npx skills add mattpocock/skills --skill domain-modeling
```
