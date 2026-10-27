---
name: new-project
description: "Compose a new project from an interview and a proposed pack set, with no folder made before the human agrees. Use on 'new project', 'start a project', 'set up a project here', or when a folder is about to become a project."
disable-model-invocation: true
kind: orchestration
agents: [doc-writer]
stops: [the composition agreed before any folder exists, the adopt agreed where the target already has content]
status: active
bindings: []
removal-date: null
---

# new-project

## What this is

**A project is composed in conversation, agreed by the human, and only then written.** This skill turns "start a project" into an interview, a proposal from the base's catalog, the human's agreement on the composition and the target, a scaffold, the target's bindings filled by `doc-writer` from the human's answers, a green `validate`, seeded state, and a handoff for the first working session.

> Nothing is written before the composition is agreed. Every answer about the new project comes from the interview, never from the place it is created in.

## Bindings

- No binding of the project this skill runs in is consulted. The skill runs in project zero, whose own `vc` and `verification` answers are `none`; reading them would impose the root's answers on every project created under it. Every answer about the new project comes from the interview (step 1) and is written into the target by `doc-writer` (step 6).
- The one binding read is the **target's** `vc`, at SEED STATE, after BINDING INTERVIEW has written it: looked up in the target's `.claude/bindings/`, in the file of the pack that the target manifest's `bindings` map names for `vc`. Absent → record the version-control init as still TODO in the target's `memory/STATUS.md` and say so.
- Agents — `doc-writer` missing → stop before SCAFFOLD, the first write, and say so.

## Workflow

Every command is written `harness.py <verb> …` and runs as the base's `scripts/harness.py`. Inside a project, the base is the one the manifest names. Walk up from the working directory one directory at a time. A directory holding `.claude/harness.json` is the project. Otherwise, a directory holding a `.git` entry is a git root without a manifest: it is not a composed project, never inside an ancestor project, and the walk stops there. Otherwise, go up. Its manifest's `base` is resolved against the project. Where no manifest is found, `list` and `scaffold` default to the base the script sits in. `validate` reads the base from the target's own manifest and needs only `--root`.

1. **INTERVIEW** — at most six questions: what kind of work; engine or none; version control; where process and product docs live; single-domain or several; anything unusual — plus the target path. A question the opening message already answered is skipped. The interview asks about tooling only; a question about the deliverable's content is deferred to session zero, the project's first design topic. A content question is noted for HANDOFF's brief, under its Open questions, and not answered here. Content in the opening message only names session zero's topic: the PM names the topic and does not design it.
2. **CATALOG** — `harness.py list --json`. It returns the packs, each with kind, version, status, description, triggers, requires, conflicts, bindings and presets, and then the presets.
3. **PROPOSE** — match a preset or compose a custom set: one line per pack saying why it is in, one line per notable exclusion. Prefer the minimal set; adding a pack later is one command. An answer naming a pack the base does not hold is answered with the catalog, never guessed.
4. **HARD STOP — the composition gate.** The human agrees the composition and the target before any folder exists. This is the composition gate; the project's G0 is its first design topic's. Nothing is written before it.
5. **SCAFFOLD** — `harness.py scaffold <path> --preset <name>`, or `--packs <a,b,…>`; the two combine, the preset's packs unioned with the named ones, and `core` and `design-track` are always added, `design-track` wherever the base ships it.
   - **Where the target already has content** — it exists and holds anything but `.git` — **STOP** for the second agreement. Tell the human that present files are skipped unopened and left unledgered, and that an existing `CLAUDE.md` gains only the managed block. Only on the human's agreement does the command carry `--adopt`.
   - **`--adopt` is never combined with `--parent`.** The script rejects the pair.
   - Read the run by its report lines: the head `scaffold: <target>` or `adopt: <target>`; `  preset: <name>` or `  preset: none`; under `--adopt`, one `  skipped (already present): <dest>` per skip and `  CLAUDE.md: managed block ` followed by `rewritten between the existing markers`, `inserted after the first heading` or `inserted at the top (no heading)`; `  bindings to fill: .claude/bindings/<pack>.md (<keys>), …` or `  bindings to fill: none`; and the tail `<verb>: wrote N files into <target>`, followed by `, skipped M` under `--adopt`.
   - Where the target sits under an ancestor project, the notes also carry the three exclusion note forms: `  ancestor exclusions: <patterns> (ancestor projects: <rel>, …)`; `  ancestor exclusions not written: .claude/settings.json already present; add <patterns> to its claudeMdExcludes`; and `  ancestor exclusion not written for <rel>: <reason>; add an absolute pattern to .claude/settings.local.json`, where `<reason>` is `it shares this project's directory name <name>`, `its name <name> holds a glob character` or `it has no directory name`. Tell the human every `not written` line, with the patterns or the reason it names: the target's VALIDATE fails V16 until those patterns are added.
   - A refusal is one stderr line, `<verb>: refused — <reason>`, at exit 1 with nothing written: report it to the human with its reason. `target <target> is already a project; grow it with add` is answered by pointing at `add-pack`; a changed composition goes back through step 4.
   - A failure, `<verb>: failed — <failure>; the partial target <target> was left in place`, names the partial target left behind: report it and stop the skill.
6. **BINDING INTERVIEW** — for each file and key on the `  bindings to fill:` line, which lists required keys only, ask what step 1 did not already answer. Then file `.scratch/doc-writer-<slug>-brief.md` from `.claude/references/core/decision-brief.md`, carrying the human's answers as the decision record and the target's `.claude/bindings/<pack>.md` as its one target, and dispatch `doc-writer` through the Agent tool without a `name`. One brief per bindings file; the dispatches run serially. A bindings file the adopt skipped is absent from that line and is not rewritten: it is project-owned. Every answer is the human's, cited in the brief; the PM may propose defaults but never rules a slot. The decision record carries, for each slot, the question asked and the human's answer, step 1's where step 1 answered it. A default the PM proposes is an answer only where the human rules it explicitly, "take the recommended defaults" included. A slot the human did not answer takes no value: its line says so, and the slot is left to step 7.
7. **VALIDATE** — `harness.py validate --root <target>`. Green is the last line `validate: PASS` at exit 0. A failure is fixed by a further `doc-writer` brief or recorded as still TODO.
8. **SEED STATE** — the target's `memory/STATUS.md`, with the composition and the first open item: session zero, the project's first design topic. Then the version-control init, as the target's `vc` binding says (see `## Bindings`). `none` is a filled value and reads as no init.
9. **HANDOFF** — written for the first working session, through core's `handoff` skill, as the creating session's last act: its first step is `g0-open` on session zero, the design topic for the deliverable. That step is the first of the brief's Next steps, the topic named as step 1 says; the brief's Open questions carry the content questions step 1 deferred; and the brief notes that the composition may be revisited through `add-pack` once session zero's design is locked. The creating session then does no work in the new project, whether or not `handoff` launches the next session. Where the brief is written, and any launch, are `handoff`'s.

The composition and the adopt are the human's; the bindings files are `doc-writer`'s; the commands, the state file and the handoff are the PM's.
