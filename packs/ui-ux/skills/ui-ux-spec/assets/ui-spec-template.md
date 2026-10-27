---
type: ui-spec
topic: <the surface this spec covers>
tags: [<the surface>, <the area it belongs to>, <the platform where one applies>]
status: draft   # draft | stable — draft is the design-intent mode, stable the as-built one; this is the ONLY place the document states which mode it is in
updated: <YYYY-MM-DD>
sources:
  - <the source of truth every as-built claim was verified against, or the dated direction the intent is sourced to>
  - <the antecedent spec for this surface, where there is one>
  - "<Session direction YYYY-MM-DD (...)>"
---

# <The surface this spec covers>

<!-- ONE surface, ONE document, ONE mode. The mode is the caller's answer and is stated once, in the frontmatter `status`. THREE TIERS of slot. Tier 1 is FIXED in both modes and is never deleted: this frontmatter, this H1, `## How this surface relates to the ones beside it`, `## Why this surface exists`, and the closing `## Open questions` — which the `ui-spec-complete` check requires. Tier 2 is MODE-CONDITIONAL: `## Realization status`, `## Change log` and `## Glossary` are present in as-built mode and absent in design-intent mode, because nothing is realized, there is nothing to diff against, and no vocabulary has shipped. Tier 3 is OPTIONAL BY DEPTH in either mode: delete an optional section whole rather than leaving it empty. Platform-specific content is an optional ROW inside a tier-3 section and never a section of its own — this is a UI/UX template, not one platform's. Delete these guidance comments as you fill each section. -->

<!-- DESIGN-INTENT MODE ONLY — REQUIRED in that mode, deleted in as-built mode: -->
> **Design intent, not as-built.** This surface does not exist yet. Every statement below is the shape it is intended to take, sourced to the dated direction in `sources`; nothing here has been verified against a build.

## TL;DR

<!-- OPTIONAL. Delete this section where the spec is short enough to read whole. Three to five lines: what the surface is, who reads it, and the one thing it must get right. -->

## How this surface relates to the ones beside it

<!-- FIXED in both modes. The adjacent surfaces by name, and what each owns that this one does not — so a reader can tell where this spec stops. Name them; do not absorb them. Where a relationship is a dependency rather than a neighbouring, say which way it runs. -->

## Why this surface exists

<!-- FIXED in both modes. The need the surface answers and the decision behind its shape, not a description of what it looks like. OPTIONAL ROW where the platform calls for it: whether the surface is diegetic — part of the world the user is in — or overlaid on it, and why that framing was chosen. -->

## Realization status

<!-- TIER 2 — AS-BUILT MODE ONLY. Delete this section whole in design-intent mode. Which parts of the surface are built and which are not, stated as the document's own words about itself, with the source each was verified against. -->

## Change log

<!-- TIER 2 — AS-BUILT MODE ONLY. Delete this section whole in design-intent mode. What changed against the antecedent named in `sources`, one row per change, so a reader of the older document can find what moved. -->

| Date | What changed | Against |
|---|---|---|
| <YYYY-MM-DD> | <what moved> | <the antecedent section or document> |

## Design philosophy

<!-- OPTIONAL. Delete this section where the surface inherits the project's pillars without adding to them. The two or three pillars this surface is judged against, each with the consequence it has for a decision below. A pillar with no consequence is decoration. -->

## Placement

<!-- OPTIONAL. Delete this section where placement is not a decision. Where the surface sits, what it sits relative to, and what it must not occlude. OPTIONAL ROWS where the platform calls for them: whether placement is body-relative, head-relative or world-anchored; and the device or form factor the placement was decided for, named rather than assumed. -->

## Visual composition

<!-- OPTIONAL. Delete this section where the surface has no composition of its own. Layout, hierarchy, readout formats, and the colour and type decisions this surface makes — each stated as a constraint a reader can check, and each honouring the visual-language constraints the project's binding names or saying explicitly that it supersedes one and why. -->

## Behaviour and interaction

<!-- OPTIONAL. Delete this section where the surface is static. What the surface does, when it appears and hides, and which state drives each change. The input-scheme table carries one row per modality the project's binding says its surfaces target — pointer and keyboard, touch, gamepad, and, as OPTIONAL ROWS where they apply, hand-tracking and controller. Delete the rows that do not apply; do not delete the table's shape. -->

| Modality | Action | Result | State that gates it |
|---|---|---|---|
| <pointer / touch / gamepad / hand-tracking / controller> | <what the user does> | <what the surface does> | <the state this depends on, or none> |

## Hard constraints

<!-- OPTIONAL. Delete this section where the surface has none. The things that are not negotiable — a budget, a legibility floor, a safety rule, a platform requirement — each with where it comes from. A constraint with no source is a preference. -->

## <Named feature> in depth

<!-- OPTIONAL, repeatable. Delete these sections where no part of the surface needs its own treatment. One section per named feature that is too large for the sections above, titled by the feature rather than by "details". -->

## Glossary

<!-- TIER 2 — AS-BUILT MODE ONLY. Delete this section whole in design-intent mode. The terms the shipped surface uses, defined once, so two documents about this surface do not name one thing twice. -->

## Open questions

<!-- FIXED in both modes, CLOSING, and required by the `ui-spec-complete` check — never deleted, even when it holds one line saying none are open. One row per question, recorded rather than resolved: what is open, what it blocks, and who rules it. The ruling is the human's, taken at the skill's second stop and written where the project's binding puts rulings. -->

| # | Question | What it blocks | Who rules it |
|---|---|---|---|
| 1 | <what is open> | <what cannot proceed until it is settled, or nothing> | <the role, per the project's Review and ruling answer> |
