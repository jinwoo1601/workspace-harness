---
name: ui-ux-spec
description: "Author one UI/UX surface spec, design-intent or as-built, leaving what it records to the human's ruling. Use when a surface needs its spec written, or a built surface's spec has to be brought up to what shipped."
kind: orchestration
agents: [designer]
stops: [the produce-mode and scope before the brief is filed, the ruling on the open questions the spec records]
status: active
bindings: [ui-ux-specs, vc, board]
removal-date: null
---

# ui-ux-spec

## What this is

A UI/UX spec is **one document per surface in one of two produce-modes**, never one document per mode. The mode is the caller's answer, not a property of the tree: `design-intent` states the shape a surface is intended to take, and `as-built` records the shape one has. The same fixed slots carry both — the frontmatter, the H1 naming the surface, how the surface relates to the ones beside it, why this surface exists at all, and the closing open questions — and three sections are structurally impossible before something is built, so they are present in as-built and absent in design intent, named in both places so neither mode is defined by what the other leaves out.

The anchor idea, and the test of every line:

> **A craft has no green build, so an as-built claim is only worth what it was verified against.**

What this craft has in place of tests is a review and a human's ruling, so the discipline that replaces a passing suite is verification: every claim an as-built spec makes is checked against the `ui-ux-specs` binding's *Source of truth* answer before it is written, and a claim that cannot be checked there is reported rather than written. A spec that states as fact what nobody verified is the failure mode this skill exists to prevent, and a spec whose open questions the author quietly resolved is the second.

## Bindings

- `ui-ux-specs` (required) — where specs live and how one is named, what an as-built claim is verified against, which visual-language constraints a spec must honour, which platforms and input modalities the surfaces target, and who reviews a spec and where the ruling is written. Absent → stop and say so **before any brief is filed**: the skill has no other route to where the spec goes or to what its claims are checked against, and every slot of the key admits an explicit `none`, so an absent key is a missing answer rather than an empty one.
- `vc` (required) — the branch procedure for the work the spec covers, and the check-in procedure that lands the spec with the change it describes. Absent → stop and say so: an as-built spec checked in apart from what it describes starts drifting on the same day it is written.
- `board` (optional) — where cross-session state lives beyond `memory/STATUS.md`, and therefore where this surface's row is updated. Absent → `memory/STATUS.md` is the state; orient from what the project binds.
- Agents — `designer` missing → stop after SETTLE and say so.

## When it applies — and prerequisites

Trigger: a surface needs its spec written, or a surface that has been built needs its spec brought up to what shipped. Before drafting, confirm:

- **The surface is named and bounded.** One spec per surface; a spec covering two surfaces settles neither, and the adjacent ones are named in the relationship slot rather than absorbed.
- **The mode is chosen, not detected.** The human chooses it at the first stop, and it goes into the brief's `Mode` field. `designer` refuses a brief that leaves it out rather than guessing from the tree.
- **The source of truth is nameable.** In as-built mode, the code paths or shipped configuration each claim is checked against; in design-intent mode, the dated human direction the intent is sourced to, quoted verbatim. Where neither exists, there is nothing to write a spec from yet.
- **You will not rule.** Who reviews a spec in place of tests and where the ruling is written is the `ui-ux-specs` binding's answer, and the ruling itself is the human's at this skill's second stop.
- **A contradiction with a locked process doc stops the work.** Where the surface as built contradicts a locked decision, that is a design action on a design branch, re-locked at G1 — never a correction written quietly into the spec.

## Workflow

1. **ORIENT** — confirm the surface and its boundary, the spec's destination and name per the `ui-ux-specs` binding, the branch per the `vc` binding's branch procedure, and the cross-session state per the `board` binding. Nothing is drafted before the surface and the mode are agreed.
2. **GATHER** — read what the spec is written from: the antecedent spec for this surface where there is one, the visual-language constraints the binding names, the related surfaces and the link targets the spec will cite, and the source of truth itself — the code paths in as-built mode, the dated direction in design-intent mode. Cite each; an uncited claim is a recollection.
3. **SETTLE** — the PM and the human work out the surface's scope and the produce-mode in conversation: which surface, which of its parts, which adjacent surfaces are named rather than covered, which platforms and input modalities apply, and which depth tiers this spec actually needs. `designer` records decisions and makes none, so nothing agreed here may be left for it to invent.
4. **STOP — the human's choice of produce-mode and the surface's scope.** The first hard stop, and it is before any brief is filed: the mode and the boundary are the two things a returned spec cannot be corrected into, because both change which sections exist.
5. **BRIEF** — file `.scratch/designer-<surface>-spec-brief.md` on the common brief fields of `.claude/references/core/brief-fields.md`, extended with: the `Mode` field carrying the settled word, the surface and its boundary, the antecedent to diff against, the source of truth by path or quoted direction, the related documents and their link targets, the platform and input modalities where they apply, the visual-language constraints to honour or supersede, the state dependencies, what is out of scope and why, and the questions to record rather than resolve. Name `assets/ui-spec-template.md` as the skeleton and the destination and file name per the `ui-ux-specs` binding. Dispatch `designer` through the Agent tool without a `name`.
6. **REVIEW** — read the returned report before the spec: the claims it declined to write because the source of truth did not carry them, and the open questions it recorded. A declined claim is a gap in the source of truth, not a gap in the spec — it goes back to GATHER or to the questions the human rules on, never into the document unverified.
7. **STOP — the human's ruling on the open questions.** The second hard stop, and the point where R7's "a human's ruling in place of tests" actually bites. The reviewer the binding's *Review and ruling* slot names reads the spec; the human rules; the ruling is written where that slot says, dated and attributed to the role rather than to a name. A question the human does not settle stays in the spec's open-questions section rather than being closed by silence.
8. **FILE** — the spec and the change it describes in one changeset per the `vc` binding's check-in procedure; the surface's row updated where the `board` binding says, or in `memory/STATUS.md` where none is bound.

## The quality bar

Every spec must clear these.

1. **One surface, one document, one mode.** The mode is stated once, in the frontmatter `status`, and the stub callout carries it in design-intent mode.
2. **Every as-built claim is verified against the source of truth.** What could not be verified is reported, not written.
3. **The tier-2 sections match the mode.** Realization status, change log and glossary are present in as-built and absent in design intent — absent because the mode forbids them, which the mode's own word makes readable.
4. **The relationship slot names the adjacent surfaces** rather than absorbing them, so a reader can tell where this spec stops.
5. **The rationale says why this surface exists**, not what it looks like. A spec that cannot say why is describing a screen rather than specifying a surface.
6. **Platform-specific content is a row inside a shared section**, never a section of its own — the craft is UI/UX, not one platform's UI/UX, and the binding's *Platform and input modalities* answer decides whether such a row applies at all.
7. **Optional depth is omitted whole, not left empty.** A section the surface does not need is deleted; an empty heading reads as an unanswered question the check cannot see.
8. **The open questions are recorded, not resolved.** Each with what it blocks and who rules it. The ruling is the human's, at the second stop.

## Filing and bookkeeping

- **Location and name:** where the `ui-ux-specs` binding's *Spec location* slot says, in the naming form it fixes. The spec and the change it describes are checked in together per the `vc` binding.
- **Shaped by** `assets/ui-spec-template.md`, whose tier-3 slots are used only where this surface has them and omitted whole where it does not.
- **Update the cross-session state** where the `board` binding says; no board bound → `memory/STATUS.md` is the state.
- **Do not touch the product surface.** A UI/UX spec is a process document. Product docs are written after G2 by the agent that reconciles them; cross-linking to one is fine, writing one from here is not.
- **Check in only when the human asks**, per the `vc` binding's check-in procedure.
