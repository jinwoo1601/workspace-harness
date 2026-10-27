---
name: codex
kind: docs
version: 0.9.0
status: active
removal-date: null
description: The product-doc lane — the post-G2 reconciler for a wiki vault or a Documentation~ plus CHANGELOG layout, and the documentation review skill.
triggers: [docs, documentation, wiki, changelog]
requires: []
conflicts: []
provides:
  agents: [codex-reconcile]
  skills: [docs-review]
  references: [page-contract.md, wiki-mode.md]
  preflight-checks: []
roles:
  codex-reconcile: [Read, Edit, Write, Glob, Grep]
bindings:
  - key: product-docs
    file: bindings/product-docs.template.md
    required: false
    interview: "Where do this project's product docs live, is the layout a wiki vault or a Documentation~/CHANGELOG surface, is there a schema file for them, and which agent reconciles them after G2 — or none bound?"
---

# codex

The product-doc lane: it owns a project's product docs after G2 acceptance and nothing before it. It re-points the `product-docs` binding with its own template, whose `Layout` slot tells the reconciler which of the two layouts — a wiki vault or a `Documentation~`/CHANGELOG surface — this project keeps.
