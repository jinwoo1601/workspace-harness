# cm command reference — the git → cm translation table

On-demand reference for git → `cm` (Plastic SCM / Unity Version Control) equivalents; the `vc-checkin` agent owns the check-in ceremony and the merge runbook is this pack's other reference. Commands below are written as `cm`, the client as it resolves on PATH.

## Commands
Use these commands instead of their git equivalents:

### Status & Inspection
| Instead of git... | Use cm... |
|---|---|
| `git status` | `cm status` |
| `git diff` | `cm diff` |
| `git diff --staged` | `cm diff` (no staging area in Plastic) |
| `git log` | `cm log [csetspec] [--from=csetspec]` |
| `git log -- <file>` | `cm history <file>` |
| `git blame <file>` | `cm annotate <file>` |

Never run `cm diff` on file content — it launches a GUI difftool and hangs headless. For content comparison use `cm cat "<path>#cs:N"` into a temp file plus `diff`; for the changed-file list use `cm status` or `cm diff cs:A cs:B --format="{status}|{path}{newline}"`.

### Branching
| Instead of git... | Use cm... |
|---|---|
| `git branch` (list) | `cm branch list` |
| `git branch --show-current` | `cm wi` (the workspace's repository, branch, and/or label) |
| `git branch <name>` | `cm branch create <name>` |
| `git checkout -b <branch>` / `git switch <branch>` | `cm switch <branch>` |

### Workspaces
| Instead of git... | Use cm... |
|---|---|
| `git worktree add "<path>" <branch>` | `cm workspace create <name> "<path>" "rep:<repository>"`, then `cm switch "br:<branch>"` run in the new workspace |
| `git worktree list` | `cm workspace list` |
| `git worktree remove "<path>"` | `cm workspace delete "<path>"` |
| `git worktree move "<path>" "<new path>"` | `cm workspace move "wk:<name>@<machine>" "<new path>"`, then every other entry moved by hand |
| `git switch <branch>`, in a tree | `cm switch "br:<branch>"`, run in the workspace |
| `git branch --show-current`, in a tree | `cm wi "<path>"`, run as written from anywhere — no `cd` |

What the client does for a workspace:
- `cm workspace create` downloads nothing: the new workspace holds only `.plastic` until `cm switch` brings the branch's files.
- A workspace is a sibling directory, never nested: a create at a path inside another workspace is refused.
- `cm switch --noinput` refuses a workspace with pending changes, which stays on its branch with them.
- In Git Bash, a `br:/` spec is rewritten into a Windows path unless `MSYS_NO_PATHCONV=1` is set before `cm`.
- A Claude Code allow rule does not match past a leading `MSYS_NO_PATHCONV=1`, so the settings template allows each prefixed read by a rule of its own; and since a rule's `*` matches spaces, the preview's allow rule `cm merge * --machinereadable` would match a `--merge` too, which the template's ask rule `cm merge *--merge*` keeps behind a prompt.
- `cm workspace list` prints one line, a name and a path, for every workspace on the machine, other projects' included, and no branch; `--format` is refused. Each workspace's branch is `cm wi "<path>"`'s, run as written from anywhere — no `cd`; it prints that workspace's `Branch <branch>@<repository>@<server>` line.
- `cm status --short --compact` prints one line per pending change or private file, and nothing when the workspace is clean; it exits 0 either way, so emptiness is the signal.
- A child branch, `cm branch create "br:<parent>/<name>"`, starts from its parent's head changeset.
- `cm find branch "where name='<name>'" --nototal` matches the name at any depth, a child branch's included, and prints nothing where no branch has it; `--format="{name}"` prints each match's full name.
- `cm workspace delete` refuses nothing: it unregisters the workspace and removes only `.plastic`, leaving every file on disk, pending changes and private files included, and it keeps the branch — so a removal that must not destroy pending work reads the workspace clean first and removes the directory after.
- `cm workspace move` exits 0 having moved only `.plastic`: every other entry stays at the old path, while `cm workspace list` reads the workspace at the new path — so the exit code is no proof the files moved, and a move is finished by moving every other entry after it and reading the new path back.
- An interactive Unity Editor re-saves `ProjectSettings/PackageManagerSettings.asset` when it opens a project, leaving it a pending change; the Clean read drops it only as a plain Changed file whose bytes equal its base and keeps it checked out or changed, so whether a workspace a human has opened reads clean depends on which the re-save leaves.

### Committing
| Instead of git... | Use cm... |
|---|---|
| `git add <files>` | `cm add <files>` (for new files only) |
| `git commit -m "msg"` | `cm checkin -c "msg"` or `cm ci -c "msg"` |
| `git commit -am "msg"` | `cm ci --all -c "msg"` |

### Syncing
| Instead of git... | Use cm... |
|---|---|
| `git push` | `cm push br:/<branch>@<local_repo>@<local_server> <remote_repo>@<remote_server>` |
| `git pull` | `cm pull br:/<branch>@<remote_repo>@<remote_server> <local_repo>@<local_server>` |

### Other Useful Commands
| cm command | Description |
|---|---|
| `cm merge "br:<branch>"` | Preview merging a branch into the current workspace: without `--merge` it lists what would merge and changes nothing, and `--machinereadable` gives one line per item; `--merge` performs the merge |
| `cm resolve <file>` | Resolve merge conflicts |
| `cm find <query>` | Query repo (SQL-like): e.g. `cm find changeset "where branch='main'"` |
| `cm lock list --anystatus` | List locks, retained ones included — plain `cm lock list` shows only the locks a checkout holds |
| `cm lock unlock "itemid:<id>@<repo>"` | Release a lock by the item id `cm lock list` shows — users release their own; only an administrator releases another's |
| `cm shelveset create <file>` | Stash changes temporarily; the verbs are `cm shelveset create`, `apply`, `delete` (alias `cm shelve`) |
| `cm shelveset apply sh:N` | Restore shelved changes — `cm unshelve` does not exist |
| `cm label <name>` | Tag a revision with a label |
| `cm help` / `cm <command> --help` | Built-in help |

What the client does for a merge and a lock:
- `cm merge "br:<source>" --machinereadable`, without `--merge`, is a preview that changes nothing and exits 0, one line per item: `FILE_SRC <path> …` for a file only the source changed, `APPLY ADD <path>` for an item the source added, `FILE_CONFLICT <path> …` for a file both sides changed, and `STATUS ALREADY_CONNECTED No merges detected` alone where there is nothing to merge.
- `cm merge … --merge` on a content conflict launches the GUI client and hangs an unattended session, `--nointeractiveresolution` or not; `cm undo -r .` undoes the pending merge it leaves. `--keepdestination` resolves a content conflict headlessly, keeping the destination's side and discarding the source's.
- A lock is taken by `cm checkout` of a file a lock rule covers; `cm lock create` does nothing.
- A lock is held by the workspace, not the user: while one workspace holds it, the same user's checkout from any other workspace, on any branch, is refused — so a human's workspace holding a lockable file checked out blocks any writer that needs it, and disjoint write sets do not prevent it.
- After the check-in, the lock is retained on its branch until that branch reaches the main branch, shown only by `cm lock list --anystatus`, and a checkout from another branch is refused meanwhile.
- A child branch cut from the retaining branch's head can check the file out, taking the lock; after the child's check-in the retention sits on the child, and once the child is merged back, the parent, holding the latest revision, can check it out again.
- A merge into the main branch releases every retention, a child branch's included when its revision arrives through its parent.
- Deleting a workspace that holds a checkout orphans its lock; the same user releases it with `cm lock unlock "itemid:<id>@<repo>"`.

### Key Differences from Git
- **No staging area**: `cm add` is only for new files. Modified/deleted files are detected automatically by `cm checkin --all`.
- **Changeset-based**: Commits are called "changesets" (csets).
