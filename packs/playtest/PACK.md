---
name: playtest
kind: craft
version: 0.6.0
status: active
removal-date: null
description: The playtest craft — one sitting-record template carrying both lifecycle phases, the skill that authors the plan before the sitting is run and completes the record after it, the evidence-and-ruling review angle, and the structural preflight check the gate audit runs against a finished record.
triggers: [playtest, playtesting, sitting, "sitting record", verdict]
requires: [core]
conflicts: []
provides:
  agents: []
  skills: [playtest-sitting]
  references: [angle-roster.md, sitting-record-complete.md]
  preflight-checks: [sitting-record-complete]
roles: {}
bindings:
  - key: playtest-records
    file: bindings/playtest-records.template.md
    required: true
    interview: "Where do this project's playtest sitting records live and how is one named, where is cited telemetry preserved and what is deliberately not preserved, how does a record cite a preserved file and the point inside it, and who rules a sitting and where is the ruling written?"
---

# playtest

The playtest craft: it owns the one document a sitting produces — planned before the sitting is run with every verdict cell empty, completed after it with the verdicts, the rulings and the evidence that carry them — and the discipline that keeps a quoted number reproducible, which is preservation and citation rather than a telemetry pipeline. It requires `core` because `playtest-sitting` dispatches core's `doc-writer`, reads the `vc` and `board` keys core declares, and ships a preflight check core's gate audit runs; it conflicts with nothing, so it composes beside any other craft, engine or version-control lane. It declares one key of its own, `playtest-records`, at `required: true` — a craft has no commands to name under `verification`, so a gate audit of playtest work has nothing to resolve until a project says where its records live, where cited telemetry is preserved, how a record cites it, and who rules a sitting. Every slot of that key admits an explicit `none`, so a project that preserves no telemetry can still answer it honestly.
