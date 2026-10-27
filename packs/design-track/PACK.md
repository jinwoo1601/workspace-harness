---
name: design-track
kind: workflow
version: 0.7.0
status: active
removal-date: null
description: The design lane — the system design doc, its quality bar, and the ADR convention for a fork resolved on a design branch and locked at G1.
triggers: [design, "design doc", adr, "decision record", fork]
requires: [core]
conflicts: []
provides:
  agents: []
  skills: [system-design-doc]
  references: []
  preflight-checks: []
roles: {}
bindings: []
---

# design-track

The design lane: it owns the pre-G1 half of the design track — a system design doc that specifies a model and argues the dynamics that model produces, the quality bar the draft is judged against, and the ADR convention that records a fork once the human has ruled on it. It requires `core` because its one skill dispatches core's `doc-writer` and reads the `process-docs`, `vc` and `board` keys core declares; it declares no binding of its own and conflicts with nothing, so it composes beside any version-control or product-doc lane.
