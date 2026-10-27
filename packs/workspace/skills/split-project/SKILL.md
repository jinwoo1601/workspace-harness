---
name: split-project
description: "Split a sub-domain into its own child project, on the human's ruling. Use on 'split this project', 'make <sub> its own project', 'add a sub-domain', or when one part of a project needs different version control, verification or gates."
disable-model-invocation: true
kind: orchestration
agents: [doc-writer]
stops: [the split criterion ruled before the child is scaffolded]
status: active
bindings: []
removal-date: null
---

# split-project

## What this is

**A project splits only where its sub-domains genuinely differ.** This skill tests the split criterion first; where it holds, the human rules the split and agrees the child's packs, the child is scaffolded beneath the project with a `parent` pointer, `doc-writer` fills the child's own bindings, and `validate` confirms the child is green.

> Split when version control, verification or gate cadence differ. Otherwise add packs: a manifest with nine packs is fine.

## Bindings

- No binding of the project is consulted: whether the sub-domains differ is the human's account, and the child's answers come from the interview.
- Agents — `doc-writer` missing → stop before SCAFFOLD, the first write, and say so.

## Workflow

Every command is written `harness.py <verb> …` and runs as the base's `scripts/harness.py`. Walk up from the working directory one directory at a time. A directory holding `.claude/harness.json` is the project. Otherwise, a directory holding a `.git` entry is a git root without a manifest: it is not a composed project, never inside an ancestor project, and the walk stops there. Otherwise, go up. Its manifest's `base`, resolved against the project, is the base. Where the walk finds no project — a git root without a manifest, or no manifest up to the filesystem root — this is not a composed project: stop before PRECONDITION, because there is no project to split. `validate` reads the base from the child's own manifest and needs only `--root`.

1. **PRECONDITION** — the split criterion: the sub-domains differ in **version control**, **verification** or **gate cadence** (the issue lane). Where none of the three differs, stop and point to `add-pack`: a manifest with nine packs is fine.
2. **STOP** — the human rules that the criterion is met and agrees the child's packs, which the scaffold must name: `scaffold` refuses a run that names neither packs nor a preset.
3. **SCAFFOLD** — `harness.py scaffold <project>/<sub> --packs <…> --parent <project>`. The child manifest records `parent`.
   - A child inside the parent's discovery scope copies only its delta packs, and reaches the parent's `.claude/` by walk-up; a child that is its own git repository copies the union.
   - **No `--adopt`.** The script rejects it beside `--parent`, and a non-empty sub-directory is refused as `scaffold: refused — target <target> is not empty`. Report that refusal to the human; never route around it.
   - Read the run as `new-project` does: the head `scaffold: <target>`, the `  bindings to fill:` line, the tail `scaffold: wrote N files into <target>`; a refusal, `scaffold: refused — <reason>` at exit 1 with nothing written, is reported with its reason; a failure, `scaffold: failed — <failure>; the partial target <target> was left in place`, is reported and stops the skill.
   - Where the child sits under an ancestor project, the notes also carry the three exclusion note forms: `  ancestor exclusions: <patterns> (ancestor projects: <rel>, …)`; `  ancestor exclusions not written: .claude/settings.json already present; add <patterns> to its claudeMdExcludes`; and `  ancestor exclusion not written for <rel>: <reason>; add an absolute pattern to .claude/settings.local.json`, where `<reason>` is `it shares this project's directory name <name>`, `its name <name> holds a glob character` or `it has no directory name`. Tell the human every `not written` line, with the patterns or the reason it names: the child's VALIDATE fails V16 until those patterns are added.
4. **BINDING INTERVIEW** — for each file on the child's `  bindings to fill:` line, which names only the keys the child itself must fill, ask the human the answers. Then file `.scratch/doc-writer-<slug>-brief.md` from `.claude/references/core/decision-brief.md`, carrying the answers as the decision record and the child's `.claude/bindings/<pack>.md` as its one target, and dispatch `doc-writer` through the Agent tool without a `name`. One brief per bindings file; the dispatches run serially.
5. **VALIDATE** — `harness.py validate --root <project>/<sub>`. Green is the last line `validate: PASS` at exit 0. A failure is fixed by a further `doc-writer` brief or recorded as still TODO.

The ruling and the child's packs are the human's; the bindings files are `doc-writer`'s; the commands are the PM's.
