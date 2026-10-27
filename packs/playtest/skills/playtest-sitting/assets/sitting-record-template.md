---
type: sitting
feature: <the feature or work item this sitting judges>
topic: <the area this sitting belongs to>
status: to-run   # to-run | run | ruled — the closed vocabulary, and the ONLY place this document states its stage
updated: <YYYY-MM-DD>
sources:
  - <the requirement or design statement the expected responses are judged against>
  - <the antecedent sitting record for this subject, where there is one>
  - "<Session direction YYYY-MM-DD (...)>"
---

# <What this sitting plays>

<!-- ONE document, TWO phases. The plan phase authors everything below with every Verdict cell empty and `status` at its unrun word. The sitting phase fills those cells in place, appends the run sections, and advances `status` — it never starts a second file. Keep the fixed slots: this frontmatter, this H1, the identifier line, `## Why this sitting exists`, `## How to run`, and the lettered block tables. Every other section is marked where it stands — OPTIONAL, or required only on its own condition; delete an optional section whole rather than leaving it empty, and delete these guidance comments as you fill each section. State the stage ONLY in the frontmatter `status` — a body line announcing that the sitting is complete is the defect the `sitting-record-complete` check exists to catch. -->

**Build or branch:** <the build number, tag, commit or branch this sitting is played against — one slot, either form, filled with something a reader can reproduce>

## Why this sitting exists

<!-- What is being judged and why now: the change, the risk, or the open question that makes this sitting worth an hour. Cite the statement each block is judged against. -->

## How to run

<!-- Everything the chair — the person who runs the sitting — needs before the first trial: the build or install, the configuration and settings that differ from default, the save or scenario to load, the inputs and devices in use, and what must be captured while it runs. -->

## Blocks

<!-- One lettered block per area of the subject. A row is ONE trial judged against ONE expected response, and the expected response is written BEFORE the trial is run. The Verdict cell is the only blank the plan phase ships; the reasoning behind a verdict goes in the run section below, never in the cell. Rows are addressed as <letter><number> — A1, A2, B1 — so a trace can name the row it carries. -->

### Block A — <subject>

| # | Trial | Expected response | Verdict |
|---|---|---|---|
| A1 | <what the chair does> | <what should happen, stated before the trial> | |
| A2 | <what the chair does> | <what should happen, stated before the trial> | |

### Block B — <subject>

| # | Trial | Expected response | Verdict |
|---|---|---|---|
| B1 | <what the chair does> | <what should happen, stated before the trial> | |

## Pass / fail criteria

<!-- OPTIONAL. Delete this section where the sitting has none. Pre-declared, and declared BEFORE the sitting is run: what makes this sitting a pass overall, and what single failure is enough to stop it. Declaring them afterwards is fitting the bar to the result. -->

## Hypotheses

<!-- OPTIONAL. Delete this section where the sitting has none. What you expect to break and why, written before the sitting so the record shows which expectations survived. -->

## Evidence to preserve

<!-- REQUIRED where this record quotes a number; delete this section where the sitting cites nothing. One line per artefact: what is captured, where it is preserved per the project's telemetry-store answer, and the citation form a row or trace uses to name it and the point inside it. Evidence is preserved as it is produced and checked in with this record. -->

## Run 1 — <YYYY-MM-DD>

<!-- OPTIONAL in the plan phase, where no run has happened yet; delete it until the sitting has been run. One dated section per session — `### Run N — <date>` where a sitting spans several. It carries the observation trace: per row, addressed by its block letter and number, what was actually observed and the preserved evidence that carries it. The Verdict cell above is the claim; this is what makes it checkable. -->

- **A1 —** <what was observed, and the cited evidence behind any number quoted>
- **A2 —** <what was observed, and the cited evidence behind any number quoted>

## Findings

<!-- OPTIONAL. Delete this section where the sitting surfaced nothing. A queue, not a fix list: one line per finding with what it blocks and where it goes next — a backlog row, an issue, or a design action. A sitting surfaces; it does not resolve. -->

| # | Finding | Where it came from | What it blocks | Next |
|---|---|---|---|---|
| 1 | <what was found> | <the row or run it came from> | <what it blocks, or nothing> | <where it goes> |

## Ruling — <YYYY-MM-DD>

<!-- OPTIONAL in the plan phase; delete it until the sitting has been ruled. The ruling is the human's, taken at the skill's second stop, dated, and attributed to the role rather than to a name. Where the project's binding puts rulings somewhere else, this section cites that place instead of restating it. -->

## Close-out

<!-- OPTIONAL. Delete this section where the sitting needs none. What the sitting settled, what it deliberately left open, and what the next sitting on this subject should carry forward. -->
