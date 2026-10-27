---
name: add-pack
description: "Grow an existing project by one pack from the catalog, on the human's agreement. Use on 'add a pack', 'add <pack> to this project', 'compose in <pack>', or when a project needs a lane it does not yet compose."
disable-model-invocation: true
kind: orchestration
agents: [doc-writer]
stops: [the pack and its binding answers agreed before ADD]
status: active
bindings: []
removal-date: null
---

# add-pack

## What this is

**A project grows by one pack at a time, and only the manifest grows.** This skill runs inside an existing project: the human chooses a pack and agrees the answers its binding keys need, `harness.py add` composes it in, `doc-writer` writes the new pack's bindings file from those answers, and `validate` confirms the project is green.

> Agree first, add second, interview third, validate last. Nothing else in the project changes.

## Bindings

- No binding of the project is consulted: the pack's binding keys come from the catalog, and their answers from the human.
- Agents — `doc-writer` missing → stop before ADD, the first write, and say so.

## Workflow

Every command is written `harness.py <verb> …` and runs as the base's `scripts/harness.py`. Walk up from the working directory one directory at a time. A directory holding `.claude/harness.json` is the project. Otherwise, a directory holding a `.git` entry is a git root without a manifest: it is not a composed project, never inside an ancestor project, and the walk stops there. Otherwise, go up. Its manifest's `base`, resolved against the project, is the base. Where the walk finds no project — a git root without a manifest, or no manifest up to the filesystem root — this is not a composed project: stop before CHOOSE and point to `new-project`. `add` and `validate` read the base from the manifest and need only `--root`.

1. **CHOOSE** — the pack, named by the human or matched from the catalog `harness.py list --json` returns. An unknown name is answered with the catalog, never guessed.
2. **STOP** — the human agrees the pack **and the answers for its binding keys**, which the catalog's `bindings` field names, before anything is written.
3. **ADD** — `harness.py add <pack> --root <project>`. A refusal, `add: refused — <reason>` on stderr at exit 1 with nothing written, is reported to the human with its reason. On success, read:
   - `  added: <pack> <version>`;
   - any `  adopted: <destination>` — a file already sitting at that destination was byte-identical to the pack's copy, so `add` wrote nothing there, kept the local bytes and entered it in the ledger; the file is a pack copy now, not a local item;
   - any `  re-pointed: <key> from core to <pack>; the ## <key> section of .claude/bindings/core.md is now inert` — tell the human that the project's existing answer for that key now has to live in the new pack's file;
   - the `  bindings to fill:` line, `.claude/bindings/<pack>.md (<keys>), …` or `none`;
   - the tail `add: wrote N files into <project>`.
4. **BINDING INTERVIEW** — ask only what step 2's agreement left unanswered. Then file `.scratch/doc-writer-<slug>-brief.md` from `.claude/references/core/decision-brief.md`, carrying the human's answers as the decision record and `.claude/bindings/<pack>.md` as its one target, and dispatch `doc-writer` through the Agent tool without a `name`. One brief per bindings file; the dispatches run serially.
5. **VALIDATE** — `harness.py validate --root <project>`. Green is the last line `validate: PASS` at exit 0. A failure is fixed by a further `doc-writer` brief or recorded as still TODO.

The choice and the answers are the human's; the bindings file is `doc-writer`'s; the commands are the PM's.
