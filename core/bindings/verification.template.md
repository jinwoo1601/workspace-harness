## verification
<!-- Interview: How is this project compiled and tested from where the human works — from which directory, which commands in which order, what does green look like for each, and how are only the checks that cover one change run — and may those commands also run in a writer tree, a parallel writer's own working tree, from that tree's root? Which shell does the Bash tool run commands in, which command prints the working directory, and in which form is a path written and two paths compared? One `Command N` line per command in run order; `Targeted` a command with `<target>` where the change's checks go, or `none`; `Tree-safe` answered `yes` or `no`, unstated read as `no`; a single `none` when nothing can be run. -->
- Run from: TODO (the working directory)
- Command 1: TODO — expected green: TODO
- Failure rule: TODO (what counts as FAIL whatever the tail says)
- Prerequisites: TODO (or `none`)
- Targeted: TODO (the command that runs only the checks covering one change, with `<target>` where those checks are named — or `none` where the commands cannot be narrowed)
- Tree-safe: TODO (`yes` where the commands may also run in a writer tree — a parallel writer's own working tree — from that tree's root; otherwise `no`; unstated reads as `no`)
- Shell: TODO (the shell the Bash tool runs commands in — e.g. an MSYS2 bash on Windows, bash, zsh)
- Working-dir read: TODO (the command that prints the working directory in the Path form — e.g. `pwd -W` in an MSYS2 bash, `pwd` elsewhere)
- Path form: TODO (the form a write path takes and in which two paths are compared — e.g. Windows form `<drive>:\…`, compared case-insensitively with either separator; or POSIX, compared exactly — and any shell forms never written by, e.g. `/tmp`, `/c`, `/d` in an MSYS2 bash)
