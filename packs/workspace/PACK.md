---
name: workspace
kind: workspace
version: 0.10.0
status: active
removal-date: null
description: The composer's lane — agree a project's composition with the human, create the project from it, grow it by a pack, split it into sub-domains, and report what it composes.
triggers: [workspace, "new project", "add a pack", "split project", "list packs", composition, preset]
requires: [core]
conflicts: []
provides:
  agents: []
  skills: [add-pack, list-packs, new-project, split-project]
  references: []
  preflight-checks: []
roles: {}
bindings: []
---

# workspace

The composer's lane: it owns how a project's composition is agreed, created, grown, split and reported — the interview and the human's agreement before any folder exists, the scaffold that follows, one more pack added to a project that already runs, a sub-domain split off where version control, verification or gate cadence differ, and a report of what a project composes against what the base offers. It owns no project fact, declares no binding key, and never edits a pack in the base: every answer about a project comes from the interview and is written by core's `doc-writer` into that project's own bindings files, which is why it requires `core`; it conflicts with nothing, so it composes beside any other lane. Its place is project zero, the workspace root, where walk-up delivers its skills to the projects beneath that are not git repositories; a git project, whose walk-up stops at its own root, composes this pack itself to reach them.
