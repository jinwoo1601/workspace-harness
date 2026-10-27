# Merge ceremony — main-thread runbook (Plastic SCM)

<!-- Executed by the MAIN THREAD at the vc binding's Merge procedure, behind the human's stop at the gate — g1-lock's merge for a design branch, g2-accept's for a feature branch. Where the trees binding is filled, it runs in the hub, which stays on the main branch and is never switched — from a session in a branch tree, by that binding's Hub idiom: `cm merge` takes no workspace path, so no allow rule matches it there, and it goes to the classifier and its asks. This never moves into vc-checkin: that agent is forbidden to merge, and content conflicts need the human. -->

All commands: `cm`, paths quoted.

## 1. Pre-merge: clean workspace

`cm merge` refuses with ANY pending tracked changes ("MergeWithPendingChanges"). Where the `trees` binding is filled, the destination is the hub, on the main branch: read it clean by that binding's Clean read, run as written, before the merge, and switch nothing. Otherwise check `cm status` on the DESTINATION branch after switching.

The Clean read does not list a plain Changed file byte-identical to its base, so a hub it reads clean may still hold one; if `cm merge` still refuses with pending changes, park it as below or run `cm undo --unchanged`, an ask.

Recurring blocker — phantom-Changed files (byte-identical, re-saved by an editor or tool without a real change). Park them:

1. `cm checkout "<file>" ...`
2. `cm shelveset create "<file>" ... -c "parked for merge"`
3. `cm undocheckout "<file>" ...`

Shelve verbs are `cm shelveset create | apply | delete` (alias `cm shelve`). `cm unshelve` does NOT exist. Restore later with `cm shelveset apply sh:N` if the contents were real.

## 2. Merge

1. `cm switch <destination-branch>` — only where the `trees` binding reads absent and the workspace is on another branch; where it is filled, the hub is already on the main branch, and nothing is switched
2. `cm merge "br:<source-branch>" --machinereadable` — the preview, which changes nothing: one line per item; a line not beginning `STATUS`, `FILE_SRC` or `APPLY` is a conflict, which goes to the human by §3 before anything is merged, and `STATUS ALREADY_CONNECTED` alone is nothing to merge
3. `cm merge "br:<source-branch>" --merge`

Clean files merge and stage automatically. The merge is resumable — a conflict does not lose the staged portion.

## 3. Content conflicts → the human

A file changed by BOTH contributors in the same region launches the Windows GUI Mergetool, which hangs an unattended session (the workflow board's single long row is the classic case), and `--nointeractiveresolution` does NOT keep it away — its help names directory conflicts. The §2 preview finds such a file first, as a `FILE_CONFLICT` line, with nothing touched. `--keepdestination` does resolve a content conflict headlessly, keeping the destination's side and discarding the source's; which side wins is the human's call, so it runs only on the human's word.

Hand it to the human with this exact click path, then wait:

> In the Mergetool: **Merge ▾ → Keep destination** (or resolve by hand) → **Mark as resolved** → **Save & exit**.

Do not attempt to fight the conflict headless, and do not kill the mergetool process to "retry".

## 4. Checkin

You cannot `cm ci` while a merge is in progress ("Finish it before checkin") — resolve everything first, then `cm ci -c "<merge comment>"` (or `-commentsfile=<WINDOWS path>` for long comments).

## 5. Board update — separate commit

The workflow-board update is a SEPARATE commit after the merge checkin (merge-then-board), never folded into the merge changeset. Where the trees binding is filled and the board lives in `memory/` — outside the trees contract's exception for a hub session on its own branch — it is one hub operation: the base's `scripts/hub.py write --root <hub> …`, run as written from the session's own tree once `scripts/hub.py lock release --root <hub>` has run, never through the vc-checkin agent (`.claude/references/core/trees-contract.md` `## The hub operation`). Otherwise — the trees binding absent, or a board kept outside `memory/` — run it via the vc-checkin agent.
