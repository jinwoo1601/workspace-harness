# ui-spec-complete — the check's definition

The preflight check this pack declares under `provides.preflight-checks`, run by the gate's preflight audit as one of its items. It asserts that a UI/UX surface spec is **structurally complete**: a craft has no command a gate can run in place of a test, so what the audit can check mechanically is that the document carries the slots a reviewer's judgment has to rest on — where it came from, what it leaves open, and whether the documents it cites are still reachable. Everything about whether the design is any good is the human's ruling and is named below as out of scope.

## What it scans

The **surface specs** the `ui-ux-specs` binding's *Spec location* slot names, within the range or the set the audit names, and nothing else. Not the code the surface is built from, not specs outside the range, not any file the binding does not put under that location. It reads each spec's frontmatter, its section headings and the links it cites; it does not open the implementation, and it does not read a design tool's file.

## What counts as a hit

Three structural checks, one row per hit:

- **Frontmatter incomplete** — one of `type`, `topic`, `tags`, `status`, `updated`, `sources` absent, or present with an empty value.
- **No open questions** — no closing open-questions section. The section is fixed in both produce-modes, and a spec that records nothing open says so inside it rather than by deleting it.
- **Cited link unresolvable** — a link the spec cites whose target the check cannot resolve: an adjacent spec, a source entry or a related document that is not where the citation says it is.

**Not a hit:** an optional section the template marks optional and the spec omits whole — TL;DR, design philosophy, placement, visual composition, behaviour and interaction, hard constraints, and a named-feature deep-dive; the three mode-conditional sections — realization status, change log and glossary — absent from a spec whose mode word is the design-intent one, or present in one whose word is the as-built one; an open-questions section carrying a single line saying none are open; and a citation that resolves but whose relevance the check has no way to judge.

## What it reports

The gate auditor's three words, so the audit needs no translation:

- `PASS` — naming the specs scanned and the range or set they were taken from.
- `FAIL` — one row per hit, `<repo-relative path> — <category>`, with the remediation: fill the frontmatter key, add the open-questions section, or fix or drop the citation.
- `UNVERIFIABLE` — when the `ui-ux-specs` binding is absent or its *Spec location* slot is answered `none`, when the location it names does not exist, or when a spec's frontmatter does not parse, saying which part is not resolvable. Never silence, and never `PASS` by default.

## What it does not do

The three judgments the UI/UX recon marked human-only, each of them the document's own words about itself and each a false FAIL waiting to happen if a mechanical check tried it: whether a colour scheme reads at a glance, whether a visual reference the spec claims to honour is actually honoured, and whether a pillar the spec declares was softened in the decisions below it. It does not verify an as-built claim against the code the surface is built from — verification against the project's own source of truth is the spec author's discipline at write time, not this check's at gate time. It does not judge whether the surface is well designed, whether the mode was the right mode to write in, or whether the spec is worth its length. And it does not rule: the check reports, the human rules at the gate.

## Status

`gate-preflight` is the runner. Its audit reads the project's manifest and takes each composed pack's definition files from `.claude/references/<pack>/`, so a project composing this pack reaches this file at `.claude/references/ui-ux/ui-spec-complete.md`; the audit performs what is written above and reports it in the three words above, beside its own items. Where there is no manifest to read, the audit marks this UNVERIFIABLE and says so rather than passing it.
