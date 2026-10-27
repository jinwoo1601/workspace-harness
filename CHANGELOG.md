# Changelog

One section per release, newest first, in plain language.

## 1.1.0

1.1.0 is the harness's first public release. The entries below are what changed since 1.0.0, an
internal release that was never published, so they matter mostly to a reader comparing with that
version. A new user can start from the README.

### Added

- A stop-line hook checks how a turn ends while a skill is running: the session's last line must
  name why it stopped, as `Stop: <kind>`. A turn that ends mid-skill without one is sent back
  once; in plain conversation the hook stays silent.
- A context-bound hook: where the `session-launch` binding sets a *Context bound*, the hook adds a
  reminder after every tool call while the session's context is past it, and the session finishes
  the step in hand and hands off. It is a reminder only and refuses nothing.
- A write guard hook refuses a handoff brief written without the `handoff` skill, a direct edit of
  the main checkout's shared records where branches run in their own trees, and setting or
  editing a locked doc anywhere but on a `design-` branch.
- The rm fence, a hook on Bash calls that name `rm`: `rm` and `rmdir` run without a prompt only
  on targets inside the project, its `.scratch/`, the trees folder or the temp folders. A lone
  delete outside them asks first, one chained with other commands is denied, and a target it
  cannot read asks. A delete handed to a shell, `eval`, `xargs`, `ssh` or another runner counts
  too. Its known gaps are listed in the hooks reference each project carries.
- `harness.py automode` composes the Claude Code auto-mode entries your projects' packs ship,
  fills them from each project's bindings, and prints them with their difference from your
  user-level Claude Code settings; it writes nothing. `--apply`, which you run yourself outside
  Claude Code, replaces only the harness's own entries, and `doctor` warns, without failing, when
  they have drifted. The shipped entries let auto mode make and check in a sign-off's records when
  the ruling is yours, and take the side you ruled for one file in a catch-up merge stopped on a
  conflict.
- `scripts/hub.py write`, for projects whose `trees` binding runs each branch in its own working
  tree: it makes one record in the main checkout's shared state under a lock, commits exactly the
  paths it wrote and checks the commit holds what it wrote. A failure before the commit restores
  the paths it wrote and refuses; a commit that fails the check is kept, and the lock stays held
  for you to clear. `clear` shows and frees the lock, and `lock take` and `lock release` bracket a
  merge. It works on Git and on Plastic SCM, where `hub.py` refuses a non-ASCII main checkout
  before writing anything.
- Every skill step that records to that shared state now does it with one `hub.py write` call,
  and `write` gains `--record` to place a new record file and `--append` to add to a shared notes
  file. A refusal caused by a wrong argument prints a `correct:` line naming the argument to fix,
  and the session corrects it and runs the same record again, at most twice.
- Light lane: the `classes` binding's new *Delegated classes* slot lets a light-lane change close
  and merge without your G2-lite ruling, for the classes you name there. `harness.py close-class`
  resolves each close from its evidence and falls back to your ruling on bindings, settings,
  locked docs, an open review or a missing pre-sign-off check. Each such close is listed for you
  at your next sign-off.
- The `trees` binding gains a *Release files* slot, `none` by default, naming files every branch
  changes because they ship, such as version lines and a changelog. `g0-open` and `tackle-issue`
  set overlaps on those files aside and still show every other overlap.
- Composing a project now writes allow rules into `.claude/settings.json` for the read commands of
  `scripts/harness.py` and `scripts/hub.py` in your release clone and for `hub.py write`, and adds
  the trees folder and the main checkout to the directories Claude Code may reach. A slot it
  cannot read is reported, never refused.
- `handoff` names the session it hands off from and launches the next one; once the new session
  starts, the old one is stopped.
- `doctor` and `validate` warn when a composed skill's copy of your bindings no longer matches
  your bindings files, and the `upgrade` skill names the recompose that brings it back in line.
- Plastic SCM (`vc-plastic`): `clean-read.py`, a read-only status read that leaves out files whose
  bytes are unchanged and recovers a changed file's real name from `cm`'s garbled print of a
  non-ASCII name; `tree-remove.py`, which removes only a listed, clean workspace under the trees
  folder, even past the Windows path-length limit, and reports what it did; and allow rules for
  routine `cm` reads, `cm add` and `cm ci`, with an ask on a real `cm merge`.

### Changed

- The harness starts Python as `py`, never `py -3` or `python3`, so a machine whose `python3` is
  only the Microsoft Store alias still runs every hook. Every hook command, generated allow rule
  and the Git pre-commit shim use `py`; `--install` replaces an old shim. `upgrade` and its dry run
  list each line of your bindings and `CLAUDE.md` that still starts Python as `python3`, editing
  none of them.
- Each sign-off is put to you once. At G0, `g0-open` asks one scope question, with the story,
  track and lane shown as defaults you can change. At G2, `g2-accept` shows the audit, the checks
  only you can make and its side rulings together, and "Accept, but fix X" fixes, re-checks and
  merges without asking again unless the re-check is worse. An early word at G1, G2 or G2-lite
  stands once the checks pass.
- `g0-open` opens a feature only when it names its locked design doc and backlog row, or a locked
  design doc names it; otherwise it stops and offers a design topic. At each G2, `g2-accept` moves
  the feature's architecture and requirements docs to `status: accepted`.
- `phase-pickup` writes one plan per phase through the `architect` agent, never in Claude Code
  plan mode. It compares the plan with its build-plan row by files, scope and split, takes a
  differing plan and says so, and stops for your ruling only on work no row or requirement
  covers, a needed change to the architecture, a validator finding that conflicts with canon or
  changes the plan's scope, or a missing `plan-validator`.
- `plan-validator` checks a plan against the requirements, the architecture doc's decision
  register and the `code-mapper` report instead of sweeping the source itself, and runs its
  narrow check wherever the plan matched its row and declares no hazards. `implement` escalates a
  build loop that failed to the `debugger` and `architect` agents.
- Architecture docs: the template's component and flow sections become one `## Seams` section,
  and `## As-built deltas` entries are a few lines each; docs in the old shape are still read.
  `architecture-doc` puts the contradictions it finds and the phase breakdown to you in one
  question, the last stop before G2.
- Code the harness writes in your project carries no comment or docstring beyond a file's header
  block. Existing ones are removed only inside the definitions a plan edits, and the review's
  conventions angle checks it. `validate` on the harness itself fails any comment or docstring in
  its own code.
- Agents start without the project `CLAUDE.md`: every agent sets `omitClaudeMd: true`, `validate`
  fails one that does not, and briefs carry the project's rules in a `Project rules` field. The
  agent guard also refuses a dispatch made by an agent, and a dispatch to an agent that can
  write or run commands whose prompt names no brief file under `.scratch/`.
- `design-track` is composed into every project, whatever the preset. `doctor` and `validate`
  refuse a `process-docs` *Design docs* slot that is missing, `TODO` or `none`, and `upgrade` asks
  you for it.
- `new-project` (`workspace`) asks about tooling only, leaves content questions to the first
  session, records your answer for each binding slot, and ends at a handoff whose first step is
  `g0-open`. A slot you did not answer is left unfilled, never guessed.
- `doctor`'s size checks on architecture docs and plan files count open features only, and its
  STATUS line-length check reads its cap from the `board` binding: 200 characters while the slot
  is unanswered, no cap under `none`.
- Permissions: core now also allows `date`, `basename`, `dirname`, `od`, `sha256sum`, `seq`,
  `test`, `cygpath`, `realpath`, `sed -n`, `WebSearch` and `claude --background`, asks on in-place
  `sed -n` and the `claude` flags that widen settings, and denies `claude`'s bypass flags. `vc-git`
  allows the routine git writes and asks on `git push` and the forced `switch` form; `git branch`
  is allowed only in its exact listing forms, and its delete and force forms ask.
- `close-tree` stops at a step whose tool call is refused by permission or policy, keeps the tree,
  names the step and the refusal, and retries nothing. `review-pr` stops before it posts.

### Fixed

- `scaffold` and `scaffold --adopt` no longer crash when the release clone is on another drive
  than the project: the clone's absolute path is recorded, which ties that project to its
  machine. A clone on the same drive is still recorded relative, and one that cannot be recorded,
  such as a network path or a drive root, is refused with nothing written.
- `upgrade` repairs a locked copy's stale stored hash, and no longer reports or rewrites a
  `.claude/harness.json` that differs only in line endings. Composing skips Python bytecode in a
  pack, and `upgrade` drops a bytecode file's record, reporting it and leaving the file on disk.
  `add` writes the composed settings over an unmodified `.claude/settings.json`.
- `doctor` names a filled required binding section that lacks a template slot, and `validate`
  names a bindings file it cannot read instead of printing a traceback. A `trees` binding
  answered `- none — <reason>` now reads as absent everywhere, as `validate` reads it.
- Hooks: a deeply nested JSON input gets the hook's malformed-input answer instead of a crash that
  let the call through; a manifest that is not UTF-8 or nests too deeply is reported as invalid
  JSON; the session-start hook finds the release clone from a branch tree as `harness.py` does.
  In a checkout from before the harness the guards stay silent, while a project whose manifest is
  present and a hook script missing fails closed.
- `hub.py status line` finds a STATUS entry by its bare branch name, as the skills say, and the
  Git `tree-remove.py` runs git with `core.longpaths` on.

### Removed

- The core settings template's asks on `rm` and `rmdir`, now the rm fence's job, and the
  `Bash(find:*)` and bare `sed` allow rules.
- The `vc-git` and `vc-plastic` hook for creating a writer's tree is no longer registered while
  writer trees are not in use, and `implement` refuses its parallel-writer path meanwhile.
