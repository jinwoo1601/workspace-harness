# vc-git — autoMode fragment

A change to this fragment is a light-lane changeset, reviewed at least at slim and closed only by the human's G2-lite ruling, never delegated to the PM by class (`adr-0100`); a session meeting a refusal proposes such a change as a light-lane item and never widens this fragment in place.

Each entry under `## allow` and `## environment` is one line opening `Harness:`, the tag that tells the harness's entries from the human's own untagged ones, which are never touched; its wording is provisional → the tuning pass.

Each path and per-project fact is a named placeholder the composer fills from each project's bindings: {{root}}, the workspace root; {{trees.hub}} and {{trees.location}}, the `trees` binding's Hub and Location; {{vc.system}} and {{vc.default-branch}}, the `vc` binding's system and default branch. A line naming any of the last four is written once for each named project that composes this pack; a line naming only {{root}}, or none, is written once.

## allow

- Harness: **Git gate merges**: `git -C "{{trees.hub}}" merge [--no-ff] --no-edit <branch>` into `{{vc.default-branch}}` is the merge **Gate merges** covers, the reviewed path only under every condition that entry states.
- Harness: **Git bookkeeping commits**: `git commit` of a session's own work on its own branch, or of memory/ in the hub, is a routine reversible write under **Hub bookkeeping**, whose content rules still apply.
- Harness: **Git worktrees**: `git worktree add` and `git worktree remove`, never forced, of trees under {{trees.location}} are part of **Session control**.
- Harness: **Git catch-up conflict sides**: in a branch tree under {{trees.location}}, never in the hub {{trees.hub}}, while the catch-up merge `git merge {{vc.default-branch}}`, begun in a tree that was clean, stands stopped on a conflict, `git checkout --theirs -- <path>` or `git checkout --ours -- <path>` is a recoverable step of that merge, not Irreversible Local Destruction — `git merge --abort` restores the pre-merge tree — when `<path>` is one file that `git diff --name-only --diff-filter=U` lists and that has not been hand-edited since the merge stopped, and the side taken is the one the human ruled for that path, save a path under `.claude/` other than `.claude/bindings/`, which takes only `--theirs`, the side of `{{vc.default-branch}}`, as the base `upgrade` regenerates before the merge is committed (`adr-0112`). It does not cover `git checkout -- <path>` or `git checkout <ref> -- <path>` without `--ours` or `--theirs`, `git checkout .`, a directory or glob `<path>`, `git restore`, `git reset`, or any checkout outside an in-progress merge.

## environment

- Harness: **Default / protected branches**: the project at {{trees.hub}} has the default branch `{{vc.default-branch}}`.
- Harness: **Source control**: the project at {{trees.hub}} uses {{vc.system}}, through the `git` CLI.
