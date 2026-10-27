---
name: close-tree
description: "Close a merged branch's tree from the hub, keeping the branch, or stop a handed-off session. Use when a 'FINISHED' line or a 'STARTED' line naming a predecessor arrives, or on the human's word for a merged tree; never on 'HANDOFF' or 'BLOCKED'."
kind: execution
status: active
bindings: [vc, verification, trees, session-launch]
---

# close-tree

## What this is

The hub's half of a branch's close: the tree a finished branch was built in is removed from the hub once its checks pass, or kept with one line naming the check that failed. A report line is a trigger, never proof — a tree's close reads the `vc` binding's log read, the session list and the tree, never the report's detail, and `## A handed-off session`, which stops a handed-off session and removes nothing, takes from its line only the branch and the predecessor's session id. The removal rides on the gate ruling that authorised the merge — the G1, G2 or G2-lite ruling, or a light-lane close by class — and takes no ruling of its own (`adr-0024`).

> At a tree's close, nothing is stopped before the branch is merged, nothing is read clean while a session is at the tree, nothing is removed before the release wait, and a half-removal or a refused step is told, never retried.

## When it runs

- A `FINISHED - <branch>; lane: <lane>; <detail>` line arriving in this session → `## Workflow` for `<branch>`; the detail is never read.
- A `STARTED - <branch>; lane: <lane>; <skill>; predecessor <session id>` line arriving in this session → `## A handed-off session` for `<branch>` and `<session id>`; `## Workflow` does not run.
- The human's word on a tree `orient`'s TREES states merged and awaiting removal, proposed by its PROPOSE, or the human's word that the branch finished on a tree TREES states as "in progress, or finished with its report lost", for which PROPOSE offers this skill → `## Workflow` for that tree's branch.
- The human's word to close the tree again after a held or refused line for `<branch>` → `## Workflow` for `<branch>`.
- A `HANDOFF` or `BLOCKED` line, or a `STARTED` line naming no predecessor → nothing runs, and the line is the human's to read.

This skill never answers a report, never gives a session work, and writes nothing to `memory/`.

## Bindings

- `vc` (required) — the log read MERGED runs. Absent → stop and say so before anything runs.
- `verification` (optional) — the *Path form*, whose conversion a pack's `## The probe` may name for `<tree>`, which STOPPED's holder probes run. Absent → as that `## The probe` says; never a stop for that reason alone.
- `trees` (optional) — the Hub path and the Hub slot's idiom; the List read of TREE, MERGED and READ BACK; the Clean read of CLEAN; and the Remove procedure of REMOVE, with the held result it names where it names one, which READ BACK reads. Absent → `## Workflow` has no tree to remove: one line saying so, and it does not run; `## A handed-off session` runs with this session's project root as the tree, as it says.
- `session-launch` (optional) — the List command, the Stop command and the Confirm window, which STOPPED and `## A handed-off session` run, and the Release wait, which RELEASE waits; the Hub session name is not read, since this skill sends nothing; what the CLI behind those commands does is `.claude/references/core/claude-code-cli.md`'s. Absent, or the List command missing or `none` → STOPPED cannot run: R3's line naming the binding or the slot, and the tree kept. The Stop command or the Confirm window missing or `none` → R3's line naming the slot where a session is at the tree, and STOPPED holds where none is. The Release wait missing → RELEASE cannot run: R3's line naming the slot, and the tree kept.
- No agent: this skill dispatches nothing.

## Workflow

`<branch>` is the branch the trigger names.

1. **TREE** — the List read, run in the hub by the trees contract's hub clause (`.claude/references/core/trees-contract.md` `## The hub clause`): the tree on `<branch>`, and its path. No tree on `<branch>`, or `<branch>` is the main branch → one line saying which; stop, and nothing else runs.
2. **MERGED** — the `vc` binding's log read from the main branch to `<branch>` lists no commit, or, failing that, the same read from the branch of any other tree the List read names, run where the `vc` binding runs a log read whose destination is that branch, lists none; a tree on no branch is passed over. Otherwise R3's line, naming the branches read; nothing is stopped.
3. **STOPPED** — first the shell returns to this session's project root. Then the List command: a session is at the tree when its working directory, as the list shows it, is the tree's path or lies under it, compared as the trees contract compares paths. None → the holder probes. Any session at the tree that shows no `<id>` for the Stop command → R3's line, and nothing is stopped. Otherwise each is ended by the Stop command with its `<id>`, its conversation kept; then the List command is re-read until no session is at the tree, within the `session-launch` binding's *Confirm window*, or R3's line naming what is still listed. Then the holder probes: for each name in `.claude/harness.json`'s `packs`, in the manifest's order, `.claude/references/<pack>/tree-holder.md` where it exists, its command under `## The probe` is run once from this session's project root, `<tree>` replaced by the tree's path as TREE read it, in the form, and by any conversion call, its `## The probe` names — that call run first from the same root — in double quotes, and its exit code and output are read by its `## Reading` as held or not held — anything else, a conversion that fails or prints no path, or no command readable under `## The probe`, is unreadable. Held → the held line, and unreadable → the held line's unreadable form; either way the tree is kept, nothing is read clean or removed, no later probe runs, and the close ends. Not held → the next probe. Every probe not held, none composed, or no manifest → on to CLEAN. Nothing in this skill ends a holder: a held tree waits for the human's word.
4. **CLEAN** — the Clean read, run in the tree by the Hub slot's idiom: empty, or R3's line with what it showed.
5. **RELEASE** — where the Remove procedure waits for the directory's release itself, or the `session-launch` binding's *Release wait* reads `none`, nothing; otherwise wait the *Release wait*: a stopped session can hold its tree's directory for a few seconds after it leaves the list. The slot missing → R3's line naming it, and the tree kept.
6. **REMOVE** — the Remove procedure for the tree's path, run in the hub by the trees contract's hub clause.
7. **READ BACK** — the List read, run in the hub, and the tree's path: still listed, unlisted with its directory gone, or unlisted with its directory present, as `## Outcomes` tells them apart. Still listed, where REMOVE's output carries the held result the `trees` binding's Remove procedure names → held: the held line, `<source>` `REMOVE` and `<what the read showed>` the procedure's message; still listed otherwise → the removal refused.

**A refused step.** A tool call of any step refused by permission or policy — TREE's or READ BACK's List read, MERGED's log read, STOPPED's List command, Stop command, a holder probe or its conversion call, the Clean read, RELEASE's wait, or a command of the Remove procedure — stops the close at that step: nothing after it runs, the refused call is never retried in another form, and the human hears the refused line. A refusal is no read's result: never a failed check, never held or unreadable, and never one of READ BACK's cases.

## Outcomes

A close that ends short of `removed` tells the human one line — R3's line, the held line or the refused line — formed as `references/outcomes.md` says, beside the table of every outcome, the tree and its sessions; read it before saying the line. A removed tree is said nothing.

## A handed-off session

`<branch>` and `<session id>` are the ones the `STARTED` line names; the line is a trigger and never proof. The tree is kept: nothing is removed, read clean or written, and MERGED is not read.

1. **TREE** — as `## Workflow`'s TREE.
2. **PREDECESSOR** — first the shell returns to this session's project root. Then the trees contract's `predecessor` verb on the tree's path and `<session id>`, which decides the case where the Path form is Windows form; under another Path form this step decides the same cases by that Path form itself, as the contract says. One act per output, `<path>` the tree's path, each line one line to the human, its template plain ASCII and `<cwd>`, `<path>` and `<session id>` printed as read:
   - `stop <id>` → the Stop command with that `<id>`, its conversation kept; then the case is re-read, by the verb where the contract delivers it, until `gone`, within the `session-launch` binding's *Confirm window*, or the line `<branch>: predecessor <session id> still listed at <path>`.
   - `gone` → nothing, silently.
   - `elsewhere <cwd>` → `<branch>: predecessor <session id> not stopped - listed at <cwd>, not at <path>`, and nothing is stopped.
   - `alone` → `<branch>: predecessor <session id> not stopped - no newer session at <path>`, and nothing is stopped.
   - `no-id` → `<branch>: predecessor <session id> not stopped - no stop id at <path>`, and nothing is stopped.

The verb exiting 1 or 2 → one line to the human naming it, and nothing is stopped. Nothing is kept between lines: a replayed `STARTED` reads `gone`.

Where `trees` reads absent, the tree is this session's project root: TREE reads nothing, `<path>` is the project root, and the steps run as written.

The `session-launch` binding absent, or a slot these steps need missing or `none` → one line to the human naming it, and nothing is stopped.

At a tree's close and for a handed-off session alike, this skill writes nothing to `memory/`, keeps the branch, sends nothing to any session, and says nothing on success.

A handoff the hub takes at a step boundary of `## Workflow` or of `## A handed-off session`, or where either stops, as `handoff` `## When to hand off` says, has as its objective the next step — after the last step or a stop, the hub's next act: the next report line or the human's next word. The brief targets the hub, so `handoff` launches nothing and shows the paste line (`handoff`'s `references/launch.md` condition 3); its brief, note and pointer are `handoff`'s, not this skill's. Where `trees` reads absent, `## A handed-off session` takes no rhythm handoff: `handoff` has no hub to target there.
