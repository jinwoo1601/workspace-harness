---
name: core
kind: core
version: 0.100.0
status: active
removal-date: null
description: What every project gets regardless of domain — the gates, orientation, review, recon, and handoff machinery.
triggers: []
requires: []
conflicts: []
provides:
  agents: [architect, architect-reconcile, code-mapper, code-writer, compile-check, debugger, doc-extractor, doc-writer, finding-verifier, gate-preflight, plan-validator, researcher, review-angle]
  skills: [close-tree, g0-open, g1-lock, g2-accept, handoff, implement, orient, promote, review-cycle, upgrade]
  references: [agent-guard-hook.py, angle-roster.md, architect-author.md, architect-plan.md, brief-fields.md, claude-code-cli.md, code-writer-brief.md, coding-conventions.md, constitution-annex.md, context-bound-hook.py, debug-brief.md, decision-brief.md, delegation-contract.md, doctor-hook.py, feature-lite.md, gate-close.md, gate-packet.md, hooks.md, implementation-rules.md, prose-invariants.md, report-filer-hook.py, review-brief.md, rm-fence-hook.py, ruling-form.md, stop-line-hook.py, tool-allowlist.md, trees-contract.md, verification-fallback.md, write-guard-hook.py]
  preflight-checks: []
  settings: settings.template.json
  automode: automode.template.md
roles:
  architect: [Read, Glob, Grep, Write, Edit]
  architect-reconcile: [Read, Glob, Grep, Edit]
  code-mapper: [Read, Glob, Grep]
  code-writer: [Read, Edit, Write, Glob, Grep, Bash]
  compile-check: [Bash, Read]
  debugger: [Read, Glob, Grep, Bash]
  doc-extractor: [Read, Glob, Grep]
  doc-writer: [Read, Write, Edit, Glob, Grep]
  finding-verifier: [Read, Glob, Grep, Bash]
  gate-preflight: [Read, Glob, Grep, Bash]
  plan-validator: [Read, Glob, Grep]
  researcher: [Read, Glob, Grep, WebFetch, WebSearch]
  review-angle: [Read, Glob, Grep, Bash]
bindings:
  - key: process-docs
    file: bindings/process-docs.template.md
    required: true
    interview: "Where do this project's design docs and feature docs live — the design docs at a real location, `none` refused — what are the files called, and at which path is a phase's plan file written, and at most how many KB may an architecture doc's body, a plan file and a brief each hold, at which path pattern?"
  - key: product-docs
    file: bindings/product-docs.template.md
    required: false
    interview: "Where do this project's product docs live, is there a schema file for them, and which agent reconciles them after G2 — or none bound?"
  - key: vc
    file: bindings/vc.template.md
    required: true
    interview: "Which version-control system does this project use, and how are branches created, changes checked in, base revisions read, branches merged, the working tree recorded before an upgrade, and pull requests read, diffed and commented on?"
  - key: verification
    file: bindings/verification.template.md
    required: true
    interview: "How is this project compiled and tested from where the human works — from which directory, which commands in which order, what does green look like for each, and how are only the checks that cover one change run — and may those commands also run in a writer tree, a parallel writer's own working tree, from that tree's root? Which shell does the Bash tool run commands in, which command prints the working directory, and in which form is a path written and two paths compared? One `Command N` line per command in run order; `Targeted` a command with `<target>` where the change's checks go, or `none`; `Tree-safe` answered `yes` or `no`, unstated read as `no`; a single `none` when nothing can be run."
  - key: board
    file: bindings/board.template.md
    required: false
    interview: "Does this project track cross-session state on a board — which, and how is it read — or is memory/STATUS.md the only state? And at most how many characters may one memory/STATUS.md line carry, or is there no cap? And at most how many KB may memory/STATUS.md hold, or is there no budget?"
  - key: trees
    file: bindings/trees.template.md
    required: false
    interview: "Does this project run branches in their own working trees — where the main checkout and the trees live and how trees are named, how a branch and its tree are cut, listed, read clean, caught up with the main branch and removed, how writer branches are named, whether writer trees are pooled, and which release files every branch changes because it is shipped, each with its resolution rule — or a single `none` where every branch runs in the one checkout?"
  - key: session-launch
    file: bindings/session-launch.template.md
    required: false
    interview: "Does the PM launch sessions itself — by which command a session is started in a given tree for a given branch with a one-line prompt, keeping its transcript and in the permission mode it runs in; under which name the hub session is opened and receives the launched sessions' reports; and by which commands the running sessions are listed and a finished one is stopped; how long a launch or a stop is waited on in that list before it is read as failed; and how long a stopped session may hold its tree's directory; past how many tokens of context a session hands off inside a phase, and by which command it reads its own context — or a single `none` where the human opens every session?"
  - key: review
    file: bindings/review.template.md
    required: false
    interview: "Which review angles does each depth profile run in this project — slim, prose and full, `default` keeping the roster's own list — and which code paths are hot (per-frame, per-tick, per-event or otherwise cost-critical), where the efficiency angle EFF runs? `Hot paths` is repo-relative paths or globs, or a single `none`."
  - key: layout
    file: bindings/layout.template.md
    required: false
    interview: "Which directories hold this project's source, which its tests, and which are generated or composed output never edited by hand — or a single `none`?"
---

# core

Core is the essential pack: every project on this harness gets it regardless of domain (design §5.1). Nothing in it names a version-control system, an engine, a doc layout, or a project — what it needs from a project arrives through bindings.

`provides` lists exactly what is on disk under `core/`. `automode` names core's `autoMode` fragment, `automode.template.md` at the pack root, never copied into a project's `.claude/`. The core binding keys — `process-docs`, `product-docs`, `vc`, `verification`, `board`, `trees`, `session-launch`, `review`, `layout` — have their templates under `core/bindings/<key>.template.md`, the shape the scaffolder copies into a project's `.claude/bindings/core.md` and `doc-writer` fills — except for a key another composed pack also declares, which that pack fills: the scaffolder copies that pack's own template for the key into `.claude/bindings/<pack>.md` instead, `vc` where a version-control pack is composed being the common case; `bindings` declares each key with its template file, whether it is required, and the interview question that fills it.
