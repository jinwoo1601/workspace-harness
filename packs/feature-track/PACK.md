---
name: feature-track
kind: workflow
version: 0.32.0
status: active
removal-date: null
description: The feature lane — the requirements doc, the architecture doc and their quality bars, and the phase pickup that persists one phase's plan as its own file beside the architecture doc. A lite feature skips the requirements doc and takes its acceptance criteria from its backlog row.
triggers: [requirements, architecture, "feature doc", "phase pickup", plan]
requires: [core]
conflicts: []
provides:
  agents: []
  skills: [architecture-doc, feature-requirement-doc, phase-pickup]
  references: []
  preflight-checks: []
roles: {}
bindings: []
---

# feature-track

The feature lane: it owns the pre-build half of the implementation track — a feature-requirement doc that turns one slice of G1-locked design into a scoped, testable contract, an architecture doc that says how that contract is built and holds the build plan's breakdown and the links to its plan files, the quality bar each draft is judged against, and the phase pickup that orients, recons and persists one phase's plan as its own file beside that architecture doc. It requires `core` because its skills dispatch core's agents — `doc-writer`, `architect`, `architect-reconcile`, `code-mapper`, `doc-extractor` and `plan-validator` — and read the `process-docs`, `vc`, `board` and `product-docs` keys core declares; it declares no binding of its own and conflicts with nothing, so it composes beside any version-control or product-doc lane. A lite feature has no requirements doc: its backlog row carries its acceptance criteria (`.claude/references/core/feature-lite.md` `## The acceptance source`).
