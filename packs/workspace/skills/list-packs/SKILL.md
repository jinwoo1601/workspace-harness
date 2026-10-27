---
name: list-packs
description: "Report a project's packs and local items, or the base catalog outside a project; composition only, no drift report. Use on 'list packs', 'what does this project compose', 'what packs are there', or before choosing a pack to add."
disable-model-invocation: true
kind: execution
status: active
bindings: []
removal-date: null
---

# list-packs

## What this is

**Composition, not health.** Inside a project this skill prints what the project composes, what the base offers that it does not, and which agents and skills are local to it; outside a project it prints the base catalog and says that is what it is.

> It reports nothing about drift, hashes or whether a local file differs from a pack's copy. Version drift already fails `validate`.

## Bindings

- No binding of the project is consulted: every line comes from the manifest, the base's catalog and a directory read.
- No agent: this skill dispatches nothing.

## Workflow

Every command is written `harness.py <verb> …` and runs as the base's `scripts/harness.py`. Walk up from the working directory one directory at a time. A directory holding `.claude/harness.json` is the project. Otherwise, a directory holding a `.git` entry is a git root without a manifest: it is not a composed project, never inside an ancestor project, and the walk stops there. Otherwise, go up. Its manifest's `base`, resolved against the project, is the base. Where no manifest is found, `list` defaults to the base the script sits in.

1. **LOCATE** — walk up as above. A project → INSIDE A PROJECT. A git root without a manifest, or no manifest up to the filesystem root → OUTSIDE A PROJECT.
2. **INSIDE A PROJECT** — print three blocks:
   - **Composed** — the manifest's `packs` map, one line per pack at the version it records.
   - **Also in the base** — every pack `harness.py list --json --root <base>` returns that the `packs` map does not name, one line each: name, kind, version, description.
   - **Local** — every `.claude/agents/*.md` and `.claude/skills/*/SKILL.md` whose project-relative path is absent from the manifest's `files` map. None → say `none`.
3. **OUTSIDE A PROJECT** — print one line saying that no manifest was found and that what follows is the base catalog, not a composition; then the packs and presets `harness.py list --json` returns. This is not an error.
4. **BASE NOT FOUND** — where the manifest's `base` does not resolve to a directory, or `list` exits 1 with `list: no pack found under <root>`: print the Composed and Local blocks, which need no base, then say the base could not be found, and stop.

Every step reads; nothing is written.
