---
name: playtest-sitting
description: "Plan a playtest sitting, then complete the same record with its verdicts, rulings and evidence. Use when a build or branch is about to be played against expectations, or a chaired sitting's record has to be completed."
kind: orchestration
agents: [doc-writer]
stops: [the word on the plan before the sitting is chaired, the ruling on the completed record before it is filed]
status: active
bindings: [playtest-records, vc, board]
removal-date: null
---

# playtest-sitting

## What this is

A playtest sitting is **one document in two lifecycle phases**, never two documents. The first phase authors the plan: the subject, the build or branch it is played against, why the sitting exists, how it is run, and the lettered block tables whose row is one trial judged against an expected response — every verdict cell empty. The second phase fills those cells in place, appends the observation trace and the evidence citations that carry them, writes the dated ruling, and advances the frontmatter `status`. The skeleton is authored once; the sitting adds cells and sections to it.

The anchor idea, and the test of every line:

> **A verdict is a claim; the trace and the preserved evidence are what make it checkable a month later.**

What this craft has in place of tests is a human's ruling, so the discipline that replaces a green build is evidence: a number quoted in a record is reproducible only if the log, export or capture it came from is preserved where the `playtest-records` binding says, cited in the form that binding fixes, and checked in with the record that cites it. A record that reports a verdict no trace supports is the failure mode this skill exists to prevent.

## Bindings

- `playtest-records` (required) — where sitting records live and how one is named, where cited telemetry is preserved and what is deliberately not preserved, how a record cites a preserved file and the point inside it, and who rules a sitting and where the ruling is written. Absent → stop and say so **before any brief is filed**: the skill has no other route to where the record goes or where its evidence is preserved, and every slot of the key admits an explicit `none`, so an absent key is a missing answer rather than an empty one.
- `vc` (required) — the branch procedure for the work the sitting judges, and the check-in procedure that lands the record and the evidence it cites in the same changeset. Absent → stop and say so: the evidence discipline *is* a check-in procedure, and a citation to a file nobody checked in is not a citation.
- `board` (optional) — where cross-session state lives beyond `memory/STATUS.md`, and therefore where this sitting's row is updated. Absent → `memory/STATUS.md` is the state; orient from what the project binds.
- Agents — `doc-writer` missing → stop after SETTLE and say so.

## When it applies — and prerequisites

Trigger: a build or branch is about to be played against stated expectations, or a chaired sitting has to be completed and filed. Before drafting, confirm:

- **The subject is a build or a branch that exists**, named in the one identifier slot the template puts near the top. A sitting planned against a subject nobody can reproduce judges nothing.
- **The expected response is stated before the trial is run**, not after. A block row whose expectation is written from what was observed records an outcome, not a verdict.
- **You will not rule.** Who rules a sitting and where the ruling is written is the `playtest-records` binding's answer, and the ruling itself is the human's at this skill's second stop.
- **A contradiction with a locked process doc stops the work.** Where a sitting shows a locked decision was wrong, that is a design action on a design branch, re-locked at G1 — never a patch written into the record.

## Workflow

1. **ORIENT** — confirm the subject and the build or branch identifier, the record's destination and name per the `playtest-records` binding, the branch per the `vc` binding's branch procedure, and the cross-session state per the `board` binding. Nothing is drafted before the subject and the scope are agreed.
2. **GATHER** — read what the sitting is judged against: the requirement or design statements that fix the expected responses, the antecedent record where this subject was played before, and the findings that record left open. Cite each; an uncited expectation is an opinion.
3. **SETTLE** — the PM and the human work the plan out in conversation until the blocks are settled: which lettered blocks the sitting has, what each block covers, and for every row the trial and the expected response it is judged against. `doc-writer` records decisions and never makes one, so nothing agreed here may be left for it to invent — an empty verdict cell is the only blank the plan phase ships.
4. **PLAN** — file `.scratch/doc-writer-<subject>-sitting-brief.md` from `.claude/references/core/decision-brief.md`: the settled blocks and their rows as the decision record, `assets/sitting-record-template.md` as the skeleton, the destination and file name per the `playtest-records` binding, and the optional slots this sitting actually uses. Dispatch `doc-writer` through the Agent tool without a `name`. The brief says to keep every verdict cell empty and to leave the frontmatter `status` at the unrun word the template's own `status` line fixes.
5. **STOP — the human's word on the plan.** The first hard stop, and it is before the sitting is run rather than after it: a sitting chaired from a plan the human has not seen wastes the sitting, because the trials and their expected responses are the thing the sitting cannot fix once it is running. Present the blocks and their rows; change what the human changes; only then is the sitting chaired.
6. **CHAIR** — the sitting is run by the human. Capture what the `playtest-records` binding's *Telemetry store* slot says to preserve, at the time it is produced: a log, an export or a capture that is not preserved then is not preservable later, and a verdict resting on it becomes unfalsifiable.
7. **RECORD** — file a second brief to `doc-writer` against the **same file**: the verdict for each row, the observation trace behind it in its own subsequent section rather than in the row cell, the evidence citations in the form the binding's *Citation form* slot fixes, the run section for this date, and the frontmatter `status` advanced per the template. Never a second document, and never a PM edit of the record.
8. **STOP — the human's ruling on the completed record.** The second hard stop. The verdicts are observations; the ruling is the human's, written where the binding's *Ruling and its record* slot says, attributed to the role rather than to a name. What the sitting leaves unresolved stays in the findings queue rather than being decided here.
9. **FILE** — the record and the evidence it cites in one changeset per the `vc` binding's check-in procedure; the sitting's row updated where the `board` binding says, or in `memory/STATUS.md` where none is bound.

## The quality bar

Every sitting record must clear these.

1. **One document, two phases.** The plan phase and the record phase are the same file. A second file for the completed sitting duplicates the block tables and lets them drift.
2. **The stage is stated once.** The frontmatter `status` is the only place the document says which phase it is in. A body line announcing the sitting is complete while the frontmatter says otherwise is the defect the preflight check exists to catch.
3. **Every row is a trial judged against an expectation.** A row that describes what happened without saying what should have happened has no verdict to give.
4. **The verdict is in the cell; the trace is in its own section.** Keeping them apart is what lets a reader scan the table and still reach the reasoning.
5. **Every quoted number cites preserved evidence.** In the binding's citation form, naming the file and the point inside it. A number with no citation is an anecdote.
6. **The identifier is present and reproducible.** One build-or-branch slot, filled with something a reader can check out or install.
7. **Findings are queued, not resolved.** A sitting surfaces; it does not fix. Each finding carries what it blocks and where it goes next.
8. **The ruling is dated and attributed to a role.** And it is the human's, taken at the second stop.

## Filing and bookkeeping

- **Location and name:** where the `playtest-records` binding's *Sitting records* slot says, in the naming form it fixes. The record and the evidence it cites are checked in together per the `vc` binding.
- **Shaped by** `assets/sitting-record-template.md`, whose optional slots are used only where this sitting has them and omitted whole where it does not.
- **Update the cross-session state** where the `board` binding says; no board bound → `memory/STATUS.md` is the state.
- **Do not touch the product surface.** A sitting record is a process document. Product docs are written after G2 by the agent that reconciles them; cross-linking to one is fine, writing one from here is not.
- **Check in only when the human asks**, per the `vc` binding's check-in procedure.
