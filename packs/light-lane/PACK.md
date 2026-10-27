---
name: light-lane
kind: workflow
version: 0.25.0
status: active
removal-date: null
description: The issue and maintenance lane — one issue worked end to end, a release cut behind two human stops, and the G2-lite close, by the human's ruling or by class, of a changeset exempt from G0 and G1.
triggers: [issue, maintenance, "light lane", release, "g2-lite"]
requires: [core]
conflicts: []
provides:
  agents: []
  skills: [g2-lite, release, tackle-issue]
  references: []
  preflight-checks: []
roles: {}
bindings:
  - key: release
    file: bindings/release.template.md
    required: false
    interview: "How does this project publish a release — which repository or registry receives it, what is the release branch called, what command or workflow publishes it, which file states the version and which other files pin it, where do the release notes come from, what versioning rule applies, and what evidence says the release is good?"
  - key: issues
    file: bindings/issues.template.md
    required: false
    interview: "Where does this project track the issues light-lane work takes up — which tracker, how one issue and its thread are read and the open issues listed with their labels, how findings and questions are posted where an issue lives, and how a changeset names the issue it closes — or does the human name each task, with no tracker?"
  - key: classes
    file: bindings/classes.template.md
    required: false
    interview: "Which changesets may this project's light lane review as trivial or prose, how large may a deferral batch grow, and which classes may the PM close and merge without the human's G2-lite ruling — at most how many changed lines, summed over its files, and how many files a trivial changeset touches, which path globs every file of a prose changeset must match, at most how many items one deferral batch holds, and which of `delegated` and `audited` the PM closes — or is a slot answered `none`, which reviews every changeset it would admit at slim, or, for the closing classes, delegates nothing?"
---

# light-lane

The issue and maintenance lane: it owns the work the constitution exempts from G0 and G1 — one issue taken end to end from its report to a reviewed changeset, a release cut behind two human stops, and the G2-lite close, by the human's ruling or by class, of a changeset once it has been audited and reviewed. It requires `core` because its three skills dispatch core's `gate-preflight`, `debugger`, `code-writer`, `doc-writer` and `compile-check` and read the `vc`, `verification`, `product-docs`, `trees`, `session-launch` and `board` keys core declares; it declares three keys of its own, `release`, for the publishing facts no version-control answer carries, `issues`, for the tracker its issues are read from and answered in, and `classes`, for the bounds of its trivial and prose classes and the cap on a deferral batch, and which classes the PM closes without the human's G2-lite ruling, and it conflicts with nothing, so it composes beside any version-control or product-doc lane.
