---
name: handoff
description: "Write a focused handoff brief a cold session can start from, with one task, minimal state and exact paths. Use on 'write a handoff' or at a session's end."
kind: execution
status: active
bindings: [process-docs, vc, trees, session-launch, verification, board]
---

# handoff

## What this is

Write a **handoff brief** that another session can start from cold, with no access to this conversation. The goal is to hand off ONE focused task — not to dump this whole session. Include only what the next session needs to do that task well, and deliberately leave everything else out.

Focus of the handoff: whatever focus the human gave when invoking this skill (arguments or the free-form ask). If none was given, infer the single most likely next task from where this session left off, and state that inference in the Objective so it can be corrected.

> One task, the minimum state, every path exact. The next session reads the file, not this conversation.

## When to hand off

A session hands off at a phase boundary, or, inside a phase, at the next skill-step boundary once its context passes the bound — never below the bound merely because a step ended.

- **A phase boundary** — the start of a build-plan phase's pickup by a session that ran the previous phase's `implement`: there the session hands off whatever its context, the objective that phase's pickup.
- **A skill-step boundary** — in any skill, in any lane — feature, light and design — and between skills, once the context-bound hook's line has appeared (`.claude/references/core/context-bound-hook.py`, on `PostToolUse`, which reads the `session-launch` binding's *Context bound* after each tool call in the main thread), the session finishes the step in hand and invokes `handoff`, its objective the next step, or, after a skill's last step, the skill that follows it; the boundary it hands off at is its judgment, and a skill that must carry something across names it.
- **No line** — the *Context bound* or the *Context read* missing, `none` or `TODO`, or the hook silent → phase boundaries only; never a stop, and never a guessed figure. The *Context read* stays the human's manual read.

A session that reaches a handoff point invokes this skill itself, without waiting to be asked.

## Bindings

- `process-docs` (required) — where the design and feature docs live, so Context and Key files point at them. Absent → stop and say so before writing; a handoff that cannot point at the process docs is written from `memory/` only on the human's word, not by default.
- `vc` (required where `trees` is filled) — the current-branch read; and, wherever it is bound, the *Branch procedure*, whose forms `## Sections` item 2 reads the lane from. Where `trees` is not filled it is not otherwise consulted, and this skill runs as written. Absent where `trees` is filled → stop before writing and say so.
- `trees` (optional) — the Hub path, under which the brief and the note are written and which the `scripts/hub.py write` command that places them takes as `--root`; and the List read, which gives the path of the tree the next session opens in. Absent → today's path. Filled → the brief and the note go to the hub, as `## Where it goes` and `## The dated note` say.
- `session-launch` (optional) — the Launch command, the List command and the Confirm window, which `references/launch.md` runs, all this session's own, and the *Context bound* and the *Context read*, which the context-bound hook reads, not `## When to hand off`; what the CLI behind those commands does is `.claude/references/core/claude-code-cli.md`'s. The Hub session name, which `references/launch.md` condition 2 reads and the brief's Reporting section writes out, is the target's: read from the target tree's own bindings by the contract's lookup rooted at that tree — the `.claude/bindings/<pack>.md` there whose `## session-launch` section answers it, that tree's `CLAUDE.md` *Bindings* section as the fallback — as the contract reads `session-launch`. This session's binding absent → no launch: `## What you show me` gives the paste line. The target's binding absent, or its Hub session name missing or `none` → no Reporting section and no launch, and the paste line naming the slot; the Launch command, the List command or the Confirm window missing or `none` → the paste line naming the slot. The *Context bound* or the *Context read* missing or `none` → the hook is silent, and handoffs come at phase boundaries only, as `## When to hand off` says.
- `verification` (optional) — the *Path form*, which RUN writes the target's path in. Absent, `none` or missing the slot → no launch: the paste line naming the slot, as `references/launch.md` condition 2 says, never a stop.
- `board` (optional) — the *STATUS line cap*, which the STATUS line `## The dated note` drafts stays within. Absent, `none` or missing the slot → no cap stated, never a stop.
- No agent: this skill dispatches nothing.

## Where it goes

Write the brief to a file — **do not** print it as a copy-pasteable block.

- Path: `memory/handoffs/<YYYY-MM-DD>-<short-kebab-slug>.md` under the project root (the directory the session opened), where the slug names the objective. Where `trees` is filled, the project root here is the hub, whichever tree the session opened in: outside the exception `## The dated note` names, the brief is drafted under that final name, with no suffix read first, into the record directory that section names, and placed under the Hub path's `memory/handoffs/` by that section's placing call, the one Bash call after the drafts' Writes, which creates the directory where absent, refuses a name not of that form and, where the name is taken there, gives it `-2`, `-3`, … by its `--next-free`, inside its lock; the call's printed `brief:` line names the placed file, and the pointer line of `## What you show me` carries that file's absolute path under the Hub path.
- Create `memory/handoffs/` if it does not exist. Only where the project root has no `memory/` at all, fall back to `~/.claude/handoffs/`.
- If that exact filename already exists, append `-2`, `-3`, …, keeping the dated form `<YYYY-MM-DD>-<slug>-2.md`, rather than overwriting — where `trees` is absent, or under that exception, this session itself; where `trees` is filled, outside it, the placing call's `--next-free`, never a read before it.
- Start the file with a one-line instruction to the new session (e.g. "You're picking up: <objective>. Read the files below, then start at Next steps."), then the sections.

## The dated note

Besides the brief, write the session's dated note, `memory/<YYYY-MM-DD>.md` under the project root for today's date, created when absent. Re-read it first, since concurrent sessions share it, then append one entry at its end and edit nothing above: an H1 naming the date, the branch or task and `handoff`, then `## Summary`, `## Changes`, `## Decisions` and `## Open issues` in that order, none dropped, an empty one saying so in one line. `## Summary` names the handoff's objective and the brief's path — where the placing call below places the brief, by the token `<brief>`, which that call fills with the placed path; the other three carry what this session changed, ruled and left open that no earlier entry of the note records. The entry moves nothing out of `memory/STATUS.md`'s `## Current`, since the branch handed off is still active. Where `trees` is filled, outside the trees contract's exception for a hub session on its own branch (`.claude/references/core/trees-contract.md` `## The hub operation`), under which this skill writes as today, the note is the hub's, `memory/<YYYY-MM-DD>.md` under the Hub path, and the brief and the note are drafted into one record directory in the tree this session runs in — where the step that invoked this skill names drafts an earlier step made and did not land (`g2-accept`'s CLOSE OUT, `tackle-issue`'s STATUS), the directory holding them, `.scratch/<skill>-<slug>-record/`, `<skill>` and `<slug>` that drafting step's, else `.scratch/handoff-<slug>-record/`, `<slug>` the brief's — the note as `handoff-note.md`, the branch's STATUS line as `status-line.md`, save for a launch brief, and the commit message as `message.md`, which `handoff` redrafts where the drafting step wrote one, naming that step too. The STATUS line is the branch's `## Current` entry as one line, opening `- **` and its key, as `tackle-issue`'s STATUS draft does, its next action the brief's next step, within the `board` binding's *STATUS line cap* where one is bound. This skill's drafts are written by the Write tool, each to its file in the record directory, which the Write tool creates where absent, all issued together in one message; wherever the note, the STATUS line or the commit message cites the brief it is handing off, it writes the token `<brief>`, never the drafted name; a mention of the token itself, not a citation, is written `<<brief>>`, which the placing call writes as `<brief>`; and a literal brief name in them is left as written. Then one Bash call, the placing call, places every draft: the `scripts/hub.py write --root <hub> --message <file> … --next-free` command alone, which fills each `<brief>` token in the `--note`, `--entry` and `--message` texts with the placed brief's path, `memory/handoffs/<name>`, as its printed `brief:` line names it, plus `--predecessor` on a hand-off into this session's own tree whose brief carries the Reporting section (`## Sections` item 9), with `--main` as the trees contract says, `<hub>` the Hub path, run from this tree: the carried edits first, in their order, then `--entry Current <branch> <file>`, `<branch>` this session's branch and `<file>` `status-line.md`, only where the branch stays active — never where the carried edits remove the branch's `## Current` entry, as `g2-accept`'s CLOSE OUT's `--remove-entry Current <branch>` does, and never on the main branch, as on a hub hand-off from `close-tree` or the hub's own — then `--note <file>`, both save for a launch brief, then `--brief <file>`; the note's re-read is the command's, inside its lock, so the brief, the note and the STATUS line land as one commit. A refusal printing a `correct:` line: correct it and re-run; any other refusal, the re-run cap spent, or a lock the command holds on its own failure: BLOCKED and stop — both by the trees contract's rule (`.claude/references/core/trees-contract.md` `## The hub operation`), and nothing is launched; the directory is kept, the call landed or refused.

Where the project root has no `memory/` at all, say so and write no note: the user-level fallback under `## Where it goes` is the brief's, never the note's.

A launch brief takes no dated note: the brief `g0-open` or `tackle-issue` has this skill write for a new branch (`## Sections`) is written alone — where `trees` is filled, outside that exception, by the call above, with no `--note`, its one other edit `tackle-issue`'s STATUS entry where that step names one — the committed brief is its record, and the day's note is neither re-read nor appended to for it. That call takes `--next-free` too, and neither `--predecessor` nor the hand-off's `--entry`.

## Sections

Use these; drop any that are genuinely empty rather than padding them — except Lane, which every brief carries, and Reporting, which is present exactly where the target's `session-launch` binding reads filled with its Hub session name and the brief's target is not the hub:

1. **Objective** — the one task, in a sentence or two. Concrete and verifiable.
2. **Lane** — `design`, `feature`, `light` or `lab`: the lane of the task handed off — the work's own, or else the one its branch gives, matched against the forms the `vc` binding's *Branch procedure* names (a `<…>` placeholder matches any text): its design, feature, light-lane or lab form, the lab form `lab-<topic>` where the binding names none. A light lane's value is one ASCII line, `light, class <c>`, or for a batch `light, class <c>, batch <id>, <id>...`: the class the work declared, slim where none was.
3. **Context** — the minimum background needed to understand *why*, plus any project or workflow state that matters (active branch, gate or stage, design decisions in play). Pull from `memory/STATUS.md`, the latest session note, and the project's process docs per the `process-docs` binding. Where `trees` is filled, name the tree the next session opens in — the branch's own tree, by its path per the List read, or the hub — and say that `memory/` lives in the hub, at the Hub path, where the STATUS and the session note this section pulls from are read.
4. **Current state** — what's already done and what's in progress, so the next session doesn't redo it.
5. **Key files & locations** — exact paths (with line refs where useful) the task touches.
6. **Constraints & decisions** — locked choices, conventions, and gotchas that must be respected; things NOT to change.
7. **Next steps** — an ordered, concrete starting sequence. **State, not process:** if the next task is a workflow step, this section names the skill to invoke plus the state it needs — it never re-transcribes that skill's own steps.
8. **Open questions** — anything unresolved that needs the human's input, so the new session asks instead of guessing.
9. **Reporting** — only where the target's `session-launch` binding reads filled with its Hub session name, as `## Bindings` reads it, and the brief's target is not the hub — the target is the hub where `trees` reads filled and the next session opens at the Hub path: the text `references/launch.md` `## Reporting` gives, written into the brief as it says. Where the target is this session's own project root, that text's STARTED clause names this session as the predecessor, as `## Reporting` says: where `trees` is filled, the brief keeps the literal `<predecessor>` token and the placing call of `## The dated note` takes `--predecessor`, which fills it from `CLAUDE_CODE_SESSION_ID`, whole, and prints `predecessor: none` where that is unset or empty; where `trees` is absent, this session reads `CLAUDE_CODE_SESSION_ID` by one shell read as it writes the brief and writes the value, whole, in the token's place. Otherwise the token is removed in the draft. Unset or empty → no predecessor, and `## What you show me` says so.

Keep it tight and skimmable. Prefer precise paths and names over prose. Don't invent facts to fill a section — if something is unknown, say so.

**A launch brief for a new branch** — written when `g0-open` or `tackle-issue` invokes this skill for a branch it has just cut, naming the new tree as the target, the lane, and the skill the branch's session resumes — carries four sections, or five where Reporting applies (item 9): Objective — agree the G0 scope of the item, its line quoted, or work issue `<n>`; Lane — `design` or `feature` from `g0-open`, `light, class <c>`, or for a batch `light, class <c>, batch <id>, <id>...` from `tackle-issue`; Context — the backlog line or the issue, the new tree's path by the List read, and that `memory/` lives in the hub, at the Hub path; Next steps — invoke `g0-open`, whose branch run starts at SCOPE, or `tackle-issue` for issue `<n>`, whose resumed run goes on from DIAGNOSE; and Reporting, as item 9 says. It is placed under the hub's `memory/handoffs/` by `## The dated note`'s placing call, with no dated note, and its prompt is the paste line of `## What you show me`.

After the brief is written, where the `session-launch` binding reads filled, as the contract reads it, this session launches the next one as `references/launch.md` says; otherwise nothing is launched, and `## What you show me` gives the paste line.

## What you show me

After writing the file, where `references/launch.md` ran and CONFIRM saw the new session, output one sentence naming the objective and the file path, then CONFIRM's one line, and nothing else of substance but the `CLAUDE_CODE_SESSION_ID` line below, where it applies.

Otherwise — `references/launch.md`'s conditions not all met, or its BEFORE or CONFIRM ending in its one line, which comes first — output exactly two things, and the `CLAUDE_CODE_SESSION_ID` line below where it applies, and nothing else of substance:

1. One sentence naming the objective and the file path, so the human knows what was written. Where the next session opens in a tree other than this session's project root, the sentence also names that tree's path and tells the human to open a plain `claude` session there, never `claude -w`.
2. A single fenced line to copy-paste as the first message of a fresh session, built at run time from the file's **absolute** path:

```
Read the handoff brief at <the file's absolute path> and pick up from there.
```

Where the placing call printed `predecessor: none`, or, where `trees` is absent, item 9's read found `CLAUDE_CODE_SESSION_ID` unset or empty, either output above, the launched one or the paste-line one, ends with one line more, its one addition: `CLAUDE_CODE_SESSION_ID` was unset or empty, so the brief names no predecessor and the hub will not stop this session; close it yourself once the next session starts.

Do not reproduce the brief's contents in the conversation.
