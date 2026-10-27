---
name: vc-plastic
kind: vc
version: 0.30.0
status: active
removal-date: null
description: The Plastic SCM lane — the check-in ceremony, the cm translation table, the merge ceremony, and the WorktreeCreate hook that cuts each parallel writer's workspace and its child branch per the trees binding, parked — shipped but registered by no settings template while writer trees are parked — for a project whose version control is Plastic; the settings template also carries the cm allow and ask entries, the `clean-read.py` and `tree-remove.py` allows, and the vc-guard PreToolUse hook that refuses a subagent's state-changing cm command.
triggers: [plastic, "plastic scm", cm]
requires: [core]
conflicts: [vc-git]
provides:
  agents: [vc-checkin]
  skills: []
  references: [clean-read.py, cm-reference.md, merge-ceremony.md, tree-remove.py, vc-guard-hook.py, worktree-create-hook.py]
  preflight-checks: []
  settings: settings.template.json
  automode: automode.template.md
roles:
  vc-checkin: [Bash, Read, Grep]
bindings:
  - key: vc
    file: bindings/vc.template.md
    required: false
    interview: "Which version-control system does this project use, and how are branches created, changes checked in, base revisions read, branches merged, the working tree recorded before an upgrade, and pull requests read, diffed and commented on?"
  - key: trees
    file: bindings/trees.template.md
    required: false
    interview: "Does this project run branches in their own working trees — where the main checkout and the trees live and how trees are named, how a branch and its tree are cut, listed, read clean, caught up with the main branch and removed, how writer branches are named, whether writer trees are pooled, and which release files every branch changes because it is shipped, each with its resolution rule — or a single `none` where every branch runs in the one checkout?"
---

# vc-plastic

The Plastic SCM lane: it fills the `vc` binding's eleven slots for a project whose version control is Plastic SCM, driven through the `cm` CLI, and the `trees` binding's `cm` procedures, leaving that binding's places, names and pool to the project. Its settings template sets `worktree.baseRef` to `head`. The pack ships a `WorktreeCreate` hook, parked: no settings template registers it while writer trees are parked, so `implement` runs a plan naming units as one writer, and a background session outside any repository no longer meets the background-session guard (`.claude/references/core/claude-code-cli.md`). Registered, for each isolated agent dispatch the hook cuts a writer workspace and its writer branch — a child of the dispatching branch, which starts from that branch's head — where the `trees` binding's Location and Writer-branch naming slots say, and prints the workspace's path; it refuses a `claude -w` session, and refuses every request while `trees` is unfilled; a cut that fails is rolled back, the branch it made on the server included. The settings template also carries the `cm workspace` permission entries: it allows `cm workspace create`, and asks before `cm workspace delete`, which unregisters a workspace holding a pending change without refusing. Its `trees` Remove procedure is the script `tree-remove.py`, allowed by name in the settings template, which removes only a listed workspace beneath the trees Location that reads clean, after its directory's release, deletes the directory itself and reads back. The settings template also registers the vc-guard `PreToolUse` hook on `Bash`, which refuses a subagent's state-changing cm verb, and carries the cm read allows and the asks before destructive forms. Its `trees` Clean read is the read-only script `clean-read.py`, which drops each Changed file byte-identical to its base, allowed by name in the settings template. The pack also ships its `autoMode` fragment, `automode.template.md` at the pack root, declared as `provides.automode` and never copied into a project's `.claude/`: the Plastic SCM reads, the `cm merge` and `cm ci` form of core's gate-merge entry, and the source-control, default-branch and workspace-per-branch lines. It conflicts with `vc-git` because a project has one version-control system.
