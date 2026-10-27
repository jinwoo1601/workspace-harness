# vc-plastic — autoMode fragment

A change to this fragment is a light-lane changeset, reviewed at least at slim and closed only by the human's G2-lite ruling, never delegated to the PM by class (`adr-0100`); a session meeting a refusal proposes such a change as a light-lane item and never widens this fragment in place.

Each entry under `## allow` and `## environment` is one line opening `Harness:`, the tag that tells the harness's entries from the human's own untagged ones, which are never touched; its wording is provisional → the tuning pass.

Each path and per-project fact is a named placeholder the composer fills from each project's bindings: {{root}}, the workspace root; {{trees.hub}} and {{trees.location}}, the `trees` binding's Hub and Location; {{vc.system}} and {{vc.default-branch}}, the `vc` binding's system and default branch. A line naming any of the last four is written once for each named project that composes this pack; a line naming only {{root}}, or none, is written once.

## allow

- Harness: **Plastic SCM reads**: `cm merge ... --machinereadable` without `--merge` is a read-only merge preview. `cm find`, `cm wi`, `cm status`, `cm cat`, `cm log` and `cm workspace list` are reads. `cm cat` of a credential-shaped file is still Credential Materialization.
- Harness: **Plastic SCM gate merges**: `cm merge` into `{{vc.default-branch}}`, and the merge check-in `cm ci` that immediately follows it in the same flow, are the merge **Gate merges** covers, the reviewed path only under every condition that entry states.

## environment

- Harness: **Default / protected branches**: the project at {{trees.hub}} has the default branch `{{vc.default-branch}}` (Plastic SCM).
- Harness: **Source control**: the project at {{trees.hub}} uses {{vc.system}}, through the `cm` CLI.
- Harness: **Trusted repos**: in a Plastic SCM project each branch tree is its own Plastic workspace, one per branch.
