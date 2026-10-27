---
name: ui-ux
kind: craft
version: 0.10.0
status: active
removal-date: null
description: The UI/UX craft — one surface-spec template whose three tiers carry both produce-modes, the spec author that writes it in the mode the caller selects, the skill that settles the surface before any brief is filed, the claims-and-coupling review angle, and the structural preflight check the gate audit runs against a finished spec.
triggers: [ui, ux, "ui spec", "surface spec", "design intent"]
requires: [core]
conflicts: []
provides:
  agents: [designer]
  skills: [ui-ux-spec]
  references: [angle-roster.md, ui-spec-complete.md]
  preflight-checks: [ui-spec-complete]
roles:
  designer: [Read, Glob, Grep, Write, Edit]
bindings:
  - key: ui-ux-specs
    file: bindings/ui-ux-specs.template.md
    required: true
    interview: "Where do this project's UI/UX specs live and how is one named, what is an as-built claim verified against, which visual-language constraints must a spec honour, which platforms and input modalities do its surfaces target, and who reviews a spec in place of tests and where is the ruling written?"
---

# ui-ux

The UI/UX craft: it owns the one document a surface produces — written as the intended shape of a surface that does not exist yet, or as the record of one that does — and the discipline that keeps an as-built claim checkable, which is verifying each claim against the project's own source of truth and reporting what cannot be verified rather than writing it. It requires `core` on three of the grounds any craft does — `ui-ux-spec` dispatches an agent under core's delegation contract, reads the `vc` and `board` keys core declares, and ships a preflight check core's gate audit runs. It conflicts with nothing, so it composes beside any other craft, engine or version-control lane. It declares one key of its own, `ui-ux-specs`, at `required: true` — a craft has no commands to name under `verification`, so a gate audit of UI/UX work has nothing to resolve until a project says where its specs live, what an as-built claim is verified against, which visual-language constraints a spec honours, which platforms and input modalities its surfaces target, and who reviews a spec in place of tests. Every slot of that key admits an explicit `none`, so a project with no standing visual language and no second platform can still answer it honestly.
