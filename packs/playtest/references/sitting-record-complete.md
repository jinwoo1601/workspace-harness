# sitting-record-complete — the check's definition

The preflight check this pack declares under `provides.preflight-checks`, run by the gate's preflight audit as one of its items. It asserts that a playtest sitting record is **structurally complete for the stage it claims to be at**: a craft has no command a gate can run in place of a test, so what the audit can check mechanically is that the document carries the slots a verdict has to rest on, and that it does not report a completed sitting while its own frontmatter says it was never run — which is the live defect the corpus this pack was generalized from actually carries.

## What it scans

The **sitting records** the `playtest-records` binding's *Sitting records* slot names, within the range or the set the audit names, and nothing else. Not the telemetry store, not records outside the range, not any file the binding does not put under that location. It reads each record's frontmatter and its block tables; it does not open a cited log, export or capture, and it does not read code.

## What counts as a hit

Four structural checks, one row per hit:

- **Frontmatter incomplete** — one of `type`, `feature`, `topic`, `status`, `updated`, `sources` absent, or present with an empty value.
- **Sources unusable** — `sources` empty, or an entry that names a path or document the check cannot resolve.
- **No identifier** — no build-or-branch identifier anywhere in the record: nothing says which build, tag, commit or branch the sitting was played against.
- **Verdict missing for the stage** — a block-table row whose verdict cell is empty while the document's `status` is not `to-run`. A record still at `to-run` is *expected* to have empty verdict cells and is not a hit; a record past it is claiming a sitting happened.

**Not a hit:** an optional section the template marks optional and the record omits whole — pass/fail criteria, hypotheses, evidence to preserve, findings, the ruling, close-out, and the dated run sections; a record at `to-run` with every verdict cell empty; a block with no rows yet; and a `sources` entry that resolves but that the check has no way to judge the relevance of.

## What it reports

The gate auditor's three words, so the audit needs no translation:

- `PASS` — naming the records scanned and the range or set they were taken from.
- `FAIL` — one row per hit, `<repo-relative path> — <category>`, with the remediation: fill the frontmatter key, resolve or remove the source, name the build or branch, or complete the verdict cell.
- `UNVERIFIABLE` — when the `playtest-records` binding is absent or its *Sitting records* slot is answered `none`, when the location it names does not exist, or when a record's frontmatter does not parse, saying which part is not resolvable. Never silence, and never `PASS` by default.

## What it does not do

The three checks Ruling 4 declined, each because it needs judgment a mechanical check gets wrong and would produce false FAILs from: whether a ruling cites the evidence behind it by name; whether a ruling names the identifier it changes; and whether a finding's implication for a locked document was carried out to a design action. It does not read telemetry, and it does not verify a quoted number against the log, export or capture it came from — preservation and citation are the discipline, reproduction is not this check's. It does not judge whether a verdict is the right verdict, whether an expected response was well chosen, or whether the sitting was worth running. And it does not rule: the check reports, the human rules at the gate.

## Status

`gate-preflight` is the runner. Its audit reads the project's manifest and takes each composed pack's definition files from `.claude/references/<pack>/`, so a project composing this pack reaches this file at `.claude/references/playtest/sitting-record-complete.md`; the audit performs what is written above and reports it in the three words above, beside its own items. Where there is no manifest to read, the audit marks this UNVERIFIABLE and says so rather than passing it.
