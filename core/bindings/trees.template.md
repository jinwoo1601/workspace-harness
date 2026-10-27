## trees
<!-- Interview: Does this project run branches in their own working trees — where the main checkout and the trees live and how trees are named, how a branch and its tree are cut, listed, read clean, caught up with the main branch and removed, how writer branches are named, whether writer trees are pooled, and which release files every branch changes because it is shipped, each with its resolution rule — or a single `none` where every branch runs in the one checkout? -->
- Hub: TODO (the main checkout's path, in the `verification` binding's Path form — it stays on the main branch and holds `memory/` — and how a command runs in another tree)
- Location: TODO (where trees live beside the hub, in the `verification` binding's Path form, and how branch trees and writer trees are named)
- Create procedure: TODO (how a branch and its tree are cut from the main branch)
- List read: TODO (every tree, with its path and branch)
- Clean read: TODO (whether one tree has a pending change)
- Catch-up procedure: TODO (how a branch brings the main branch into its own tree)
- Remove procedure: TODO (how a tree is removed after its merge)
- Writer-branch naming: TODO (the branch a writer tree is cut on)
- Pool: TODO (writer trees kept for reuse, or `none`)
- Release files: none — no release class (the files every branch changes because it is shipped, each as backticked paths or globs, optionally the part meant, then ` — ` and its resolution rule, entries split by `; `)
