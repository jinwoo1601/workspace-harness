---
name: vc-git
kind: vc
version: 0.33.0
status: active
removal-date: null
description: The git lane — the inline check-in ceremony, the pull-request review lane, the no-secrets-in-diff preflight check with its pre-commit check script (a staged-change pre-commit hook installed once per clone, and the range scan the preflight cites), and the WorktreeCreate hook that cuts each parallel writer's tree per the trees binding, parked — shipped but registered by no settings template while writer trees are parked — for a project whose version control is git; the settings template also carries the git allow, ask and deny entries and the vc-guard PreToolUse hook that refuses a subagent's state-changing git command in the project's trees.
triggers: [git, github, "pull request"]
requires: [core]
conflicts: [vc-plastic]
provides:
  agents: []
  skills: [review-pr]
  references: [no-secrets-in-diff.md, pre-commit-check.py, tree-remove.py, vc-guard-hook.py, worktree-create-hook.py]
  preflight-checks: [no-secrets-in-diff]
  settings: settings.template.json
  automode: automode.template.md
roles: {}
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

# vc-git

The git lane: it fills the `vc` binding's eleven slots for a project whose version control is git, and the `trees` binding's commands, leaving that binding's places, names and pool to the project. Its settings template sets `worktree.baseRef` to `head`. The pack ships a `WorktreeCreate` hook, parked: no settings template registers it while writer trees are parked, so a platform worktree request falls to the platform's own handling, and `implement` runs a plan naming units as one writer. Registered, for each isolated agent dispatch the hook cuts a writer tree and its branch from the dispatching branch's tip, where the `trees` binding's Location and Writer-branch naming slots say, and prints the tree's path; it refuses a `claude -w` session, and refuses every request while `trees` is unfilled. The settings template also carries the `git worktree` permission entries: it allows `git worktree add` and `git worktree remove`, and asks before the removal's force forms, `--force` and `-f`, which would remove a tree with a pending change. The settings template also registers the vc-guard `PreToolUse` hook on `Bash`, which refuses a subagent's state-changing git verb, and carries the git read allows, the routine-write allows for `git add`, `git switch`, `git stash create` and `git stash store`, the `git branch` listing allows, each an exact form, the `git push` ask, the asks before destructive forms, the force forms of `git switch` and `git branch` among them, the `--no-verify` denies, the `git commit` allow, and the `tree-remove.py` and `pre-commit-check.py --range` allows; the pack also ships the pre-commit check script itself. The pack also ships its `autoMode` fragment, `automode.template.md` at the pack root, declared as `provides.automode` and never copied into a project's `.claude/`: the git forms of core's gate-merge, bookkeeping and session-control entries, its catch-up conflict-sides entry, and the source-control and default-branch lines. It conflicts with `vc-plastic` because a project has one version-control system.
