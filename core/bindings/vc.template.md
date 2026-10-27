## vc
<!-- Interview: Which version-control system does this project use, and how are branches created, changes checked in, base revisions read, branches merged, the working tree recorded before an upgrade, and pull requests read, diffed and commented on? -->
- System: TODO
- Main branch: TODO (the branch the main checkout stays on and every branch merges into, its name in backticks — e.g. `main`)
- Auto-mode entries: included (or `excluded`, where this project's packs add no entry to the autoMode block `harness.py automode` composes — a PR-only repository, for example)
- Branch procedure: TODO (the naming — by default `design-<topic>` for design work, `feat-<feature>` for feature work, `light-<topic>` for light-lane work and `lab-<topic>` for a lab experiment, which merges nothing — and how a branch is created; and the re-lock — a `design-<topic>` branch cut from the feature branch's head in the feature's own tree, declared on its STATUS line `re-lock of <feature-branch>`, merged back into that feature branch after G1 — and how it is cut and merged back)
- Check-in procedure: TODO (inline on the main thread, or the vc pack's agent)
- Base-revision reads: TODO (the commands that read a file at a revision, a diff between two revisions, the per-file line-count read — each changed file's added and deleted lines between two revisions — and the current branch)
- Merge procedure: TODO (who merges and how, behind the gate's human stop)
- Snapshot procedure: TODO (how the working tree is recorded before an upgrade writes, without changing it; the read that confirms the record; how the human restores it — or `none` where the project has no version control)
- PR read: TODO (the command that reads a pull request's metadata by its number, and the one that finds the pull request for a branch — or `none` where the project has no pull-request host)
- PR diff: TODO (the command that saves a pull request's full diff to a file — or `none` where the project has no pull-request host)
- PR comment: TODO (the command that posts a comment-only review on a pull request, and the plain comment that is its fallback — or `none` where the project has no pull-request host)
