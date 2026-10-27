# workspace-harness

## What it is

workspace-harness is a set of rules, agents, skills and hooks you install into a Claude Code
project, so that Claude works like a careful team: it decides on paper, then builds, then
stops for your sign-off.

It is for long work that runs over many sessions, where the decisions stay yours. On long work
an agent left to itself improvises: it forgets what was decided earlier, changes a decision
quietly, and declares its own work done. The harness writes each decision down, keeps it, and
leaves the sign-off with you.

## The idea

**Write it down first.** A design, and then each feature's requirements, are written before
anything is built. Docs that describe what was built come only after you accept it.

**Three sign-offs are yours.** G0: you agree the scope. G1: you lock the design. G2: you
accept the finished feature. Claude never passes one on its own judgment.

**Locked stays locked.** A locked decision is never changed quietly. If building shows it was
wrong, the work stops, and the design is reopened, amended and locked by you again.

**One session leads.** The Claude Code session you talk to is called the PM. It runs skills;
a skill hands each narrow job to an agent with a written brief, and the agent reports back.

```text
you                 rule at the three sign-offs
└─▶ PM              your Claude Code session; runs skills
    └─▶ skill       hands each narrow job to an agent, with a brief
        └─▶ agents  do the job and report back; they start no other agents
```

**Nothing is guessed.** Each project answers a set of questions about itself, called bindings:
where its docs live, how it uses version control, which checks it runs. A skill that finds a
question unanswered stops and says so.

**Rules are enforced, not only asked.** Hooks block a breach that would be silent or final,
and a validator checks the structure; written rules cover only what takes judgment.

**Small fixes take the light lane.** Issue and maintenance work skips G0 and G1, is still
reviewed, and closes at G2-lite, a lighter acceptance.

## What's in it

In the release you clone:

- `CONSTITUTION.md`: the workflow above, in full. Every project loads a copy it does not edit.
- Packs: bundles of agents, skills, hooks and references. `core` goes into every project;
  each other pack adds a track of work or a tool. `harness.py list` names them.
- Presets: named lists of packs to start a project from.
- `scripts/harness.py`: the tool behind `list`, `scaffold`, `doctor` and `upgrade`.

In each project:

- `.claude/`: the agents, skills, rules and settings composed from your packs.
- `.claude/bindings/`: your project's answers, one file for each pack that asks questions.
- `CLAUDE.md`: how your project applies the workflow. The harness rewrites the block between
  its `harness:managed` markers.
- `memory/STATUS.md`: the state your session carries from one session to the next.

You edit the bindings, `CLAUDE.md` outside that block, and your own docs and code. You don't
edit the rest of `.claude/`, which `scaffold` writes and `upgrade` rewrites, or the release
clone (see Changing the harness, below).

## Working with it

Once the walkthrough below is done, you talk to Claude Code in plain words, and the session
picks the skill. Which skills you have depends on your packs. A typical run:

- "Where are we?" The session says where things stand and names the next step.
- "Start a design topic." You agree its scope (G0). The session lays out the choices and you
  decide them. "Lock the design" (G1) locks it and breaks it into a backlog of features.
- "Open a new feature", for each feature in the backlog: you agree its scope (G0); then come
  its requirements, its architecture, and a plan for each phase. "Implement phase N" builds a
  phase; a review follows; "Accept the feature" (G2) closes it.
- "Tackle an issue." A small fix runs in the light lane and closes at G2-lite.
- Long work spans sessions: each writes a handoff brief that the next one starts from.

## Setup

Supported: Windows, with Claude Code's Git Bash. macOS and Linux are untested and unsupported.

You need:

- Git for Windows, installed with its defaults.
- Python 3.12 or newer, from python.org. Not the Microsoft Store Python: it has no `py`
  launcher. The harness starts Python as `py`, so the installer's "Add python.exe to PATH" box
  may stay unchecked.
- PyYAML and jsonschema:

  ```bash
  py -m pip install pyyaml jsonschema
  ```

- Claude Code.

## Getting a release

Clone one release tag:

```bash
git clone --branch vX.Y.Z --depth 1 <url>
```

`<url>` is `https://github.com/jinwoo1601/workspace-harness.git`, and `vX.Y.Z` is the release
you want. Below, `<clone>` is the folder this makes and `<project>` is your project's folder.

Create a project from a preset (`list` names the presets):

```bash
py <clone>/scripts/harness.py list
py <clone>/scripts/harness.py scaffold <project> --preset <name>
```

To add the harness to a folder that already has content, add `--adopt` to `scaffold`.

To update, check out a newer tag in the clone:

```bash
git fetch --depth 1 origin tag vX.Y.Z
git checkout vX.Y.Z
```

Then upgrade each project, with `--dry-run` first to see what would change:

```bash
py <clone>/scripts/harness.py upgrade --root <project> --dry-run
py <clone>/scripts/harness.py upgrade --root <project>
```

## Walkthrough: a fresh Windows machine

1. Install the tools under Setup.
2. Check Python: `py --version` prints 3.12 or newer.
3. Install the packages: `py -m pip install pyyaml jsonschema`.
4. Clone a release: `git clone --branch vX.Y.Z --depth 1 <url>`.
5. List the packs and presets: `py <clone>/scripts/harness.py list`.
6. Create a project: `py <clone>/scripts/harness.py scaffold <project> --preset <name>`. It
   prints the bindings to fill.
7. Check it: `py <clone>/scripts/harness.py doctor --root <project>`. It names each binding
   still to fill and ends `doctor: FAIL`, exiting non-zero, until they are filled.
8. Open Claude Code in `<project>` and fill the bindings `doctor` named.

Notes:

- On a fresh machine `python3` is the Microsoft Store alias, which exits 49 without running
  anything. The harness starts Python as `py`, never as `python3`.

## Changing the harness

Do not edit the clone: local edits break the next tag checkout. `promote`, which copies a file
from a project into the harness, writes into the clone, so it is not supported against a
release clone. To change the harness, fork it, and use `promote` in your fork.

## Issues and pull requests

Issues are for bug reports. Pull requests are not taken.

## Known limitations

- B132: the harness's guards fall open only with `CLAUDE_PROJECT_DIR` unset, which Claude Code
  always sets.

## License

MIT; see `LICENSE`.
