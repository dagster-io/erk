---
title: CI Label Rename Checklist
read_when:
  - renaming a GitHub label used in CI automation
  - updating label references across the codebase
  - debugging why CI label checks aren't working after a rename
tripwires:
  - action: "Renaming a GitHub label used in CI automation"
    warning: "Labels are referenced in multiple places: (1) Job-level if: conditions in all workflow files, (2) Step name descriptions and comments, (3) Documentation examples showing the label check. Missing any location will cause CI behavior to diverge from intent. Use the CI Label Rename Checklist to ensure comprehensive updates."
    score: 6
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# CI Label Rename Checklist

## Why Label Renames Are Dangerous

GitHub Actions label checks use **string literals in YAML that cannot be validated statically**. Unlike code references that fail at compile time, label mismatches fail silently:

- Boolean expressions evaluate to `false` when label names don't match
- No errors are thrown at workflow parse time or runtime
- PRs with the label run CI when they should skip (or vice versa)
- No obvious indicators point to the mismatch

The problem: **labels connect Python constants, YAML workflow conditions, and prose documentation across three different file formats with zero static validation**.

## The Coordination Challenge

<!-- Source: src/erk/cli/constants.py, PLAN_REVIEW_LABEL -->

Label definitions start in Python constants (see `PLAN_REVIEW_LABEL` in `src/erk/cli/constants.py`) but cannot be interpolated into GitHub Actions YAML. The disconnect between definition and use creates drift:

1. **Python layer**: Constants define canonical label names
2. **YAML layer**: Workflows check label strings directly in `if:` conditions and `grep` commands
3. **Documentation layer**: Docs reference label names in examples and explanations

Changing a label requires manually hunting down every reference in all three layers. Miss one location and CI behavior silently diverges.

## Comprehensive Search Strategy

When renaming a label, **grep is the only validation**:

```bash
# Find all references to old label name
grep -r "old-label-name" src/erk/cli/constants.py .github/workflows/ docs/learned/ .claude/
```

### Layer 1: Python Constants

<!-- Source: src/erk/cli/constants.py -->

Update the constant definition in `src/erk/cli/constants.py`. This is the source of truth but cannot enforce consistency elsewhere.

### Layer 2: GitHub Actions Workflows

<!-- Source: .github/workflows/ci.yml, .github/workflows/code-reviews.yml -->

Search `.github/workflows/*.yml` for:

**Job-level conditions** — Boolean expressions that skip entire jobs:

- Pattern: `!contains(github.event.pull_request.labels.*.name, 'label-name')`
- Found in: Job `if:` fields at top level

**Step-level grep checks** — Shell commands that query label via API:

- Pattern: `grep -q "label-name"`
- Found in: Multi-line `run:` blocks that call `gh api`

**Step names and comments** — Human-readable descriptions:

- Pattern: Step names like "Check label-name label"
- Pattern: Comments explaining "PR has label-name label"

All three must be updated. The workflow will parse successfully with stale label names—it just won't match anymore.

### Layer 3: Documentation

Search `docs/learned/` and `.claude/` for:

- **CI pattern docs** showing label check examples (see `docs/learned/ci/github-actions-label-queries.md`, `docs/learned/ci/workflow-gating-patterns.md`)
- **Command docs** explaining label detection logic (see `.claude/commands/erk/pr-address.md`)
- **Workflow guides** describing when labels are applied (see `docs/learned/erk/pr-address-workflows.md`)

These docs become misleading if they show old label names in examples.

## Verification Protocol

After updates, confirm zero results:

```bash
grep -r "old-label-name" src/erk/cli/constants.py .github/workflows/ docs/learned/ .claude/
```

If any matches remain, those are missed locations.

**Live test**: Create a PR, add the renamed label, verify CI behavior matches intent (skip or run as expected). Check workflow logs to confirm boolean expressions evaluate correctly.

## Why This Can't Be Automated

The root cause is **GitHub Actions' lack of variable interpolation from external sources**. Workflow YAML cannot import Python constants. This creates an unbridgeable gap:

- Python defines the canonical name
- YAML must hardcode it as a string literal
- No tooling can validate the two stay synchronized

The only validation is grep + manual review. Future improvement: Add a CI check that parses workflow YAML, extracts label strings, and validates them against Python constants. This would catch drift automatically.

## Historical Context

This checklist was created after PR #6400 fixed a `plan-review` → `erk-plan-review` mismatch that caused CI to run on PRs that should have been skipped. The label was renamed in the constant but not updated in workflow files, creating silent divergence.

## Related Documentation

- [GitHub Actions Label Queries](github-actions-label-queries.md) — Step-level API query pattern
- [GitHub Actions Workflow Gating Patterns](workflow-gating-patterns.md) — How label checks gate CI
- [Phase Zero Detection Pattern](../architecture/phase-zero-detection-pattern.md) — Uses label checks for plan review mode
