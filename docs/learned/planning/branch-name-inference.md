---
title: Branch Name Inference
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
tripwires:
  - action: "changing branch naming convention (plnd/ prefix)"
    warning: "The plnd/ prefix (planned-PR) is a cross-cutting contract used by branch creation, extraction functions, and PR recovery. Changing the prefix format requires updating all consumers. The legacy P{issue}- prefix has been fully removed."
  - action: "adding branch_name to plan-header at creation time"
    warning: "branch_name is intentionally omitted at creation because the branch doesn't exist yet. The plan-save → branch-create → impl-signal lifecycle requires this gap. See the temporal gap section below."
  - action: "recovering a branch name from a PR number using UI or truncated display"
    warning: "Use `gh pr view <pr-number> --json headRefName` to recover exact branch names. UI display may truncate long branch names."
read_when:
  - "debugging missing branch_name in plan issues"
  - "implementing PR lookup from plan issues"
  - "modifying branch creation or naming conventions"
---

# Branch Name Inference

## The Temporal Gap Problem

Plan metadata (`plan-header` block) intentionally omits `branch_name` at creation time because of a temporal gap in the plan lifecycle:

1. **Plan saved** → GitHub issue created (no branch exists yet)
2. **Branch created** → User runs `erk br co --for-plan {issue}` (branch now exists)
3. **Implementation starts** → `impl-signal started` writes `branch_name` into the plan-header

The gap between steps 1 and 2 is unavoidable: the plan must exist before the branch can be named after it (the branch name contains the issue number). Attempting to set `branch_name` during save would require either predicting the branch name (fragile — the user might choose a custom name) or creating the branch immediately (wrong — the user hasn't started work yet).

## Two-Layer Resolution

When code needs to look up a PR from a plan issue, `branch_name` may be missing from metadata. The system uses two layers:

<!-- Source: src/erk/cli/commands/exec/scripts/get_pr_for_plan.py, get_pr_for_plan -->

**Layer 1 — Metadata lookup**: Read `branch_name` from the `plan-header` block. This succeeds when `impl-signal started` ran successfully.

**Layer 2 — Git context inference** (removed): Previously, if `branch_name` was missing, the system checked whether the current git branch matched the `P{issue_number}-` prefix. This fallback was removed in PR #8269 (which deleted `get_branch_issue()`). Resolution now relies solely on Layer 1 metadata lookup and `plan-ref.json`.

If Layer 1 does not produce a match, the command fails with an actionable error.

## Branch Prefix Contracts

The inference recovery depended on **cross-cutting naming contracts**. The current format uses the `plnd/` prefix; the legacy `P{issue}-` format has been removed.

### Issue-Based Branches: `P{issue}-` (Deleted)

> **Deprecated and removed.** The issue-based plan backend and all associated branch-naming code have been deleted. `generate_issue_branch_name()` was removed, and `get_branch_issue()` (which matched `P{issue_number}-` prefixes) was deleted in PR #8269. Legacy `P{issue}-` branches may still exist in repositories but are no longer created or recognized by the system. `plan-ref.json` is the sole source of truth for all plan-to-branch mapping (PR #8071).

### Planned PR Branches: `plnd/` (Current Format)

All new plans use the `plnd/` prefix pattern. Branches follow the pattern `plnd/{slug}-{timestamp}` (with optional `O{objective_id}` segment). These branches have **no extractable plan ID** from the branch name alone. Legacy branches may use `planned/` prefix.

<!-- Source: packages/erk-shared/src/erk_shared/naming.py, generate_planned_pr_branch_name -->

- **Branch creation**: `generate_planned_pr_branch_name()` produces `plnd/{slug}-{timestamp}`
- **Plan ID resolution**: `PlannedPRBackend.resolve_plan_id_for_branch()` uses an API call, not regex
- **Source of truth**: `plan-ref.json` is the sole source of plan ID for all plan branches (both current `plnd/` and legacy `P{issue}-`)
- **Extraction functions**: `extract_objective_number()` handles `P{issue}-O{obj}-`, `plnd/O{obj}-`, and legacy `planned/O{obj}-` patterns

**Key change (PR #8071):** Plan ID encoding was removed from branch names. All plan-to-branch mapping now goes through `plan-ref.json`.

## When Inference Fails

Common failure scenarios and their fixes:

| Symptom                                | Cause                                                | Fix                                                                  |
| -------------------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------- |
| "plan-header has no branch_name field" | On wrong branch (e.g., `master`)                     | Switch to the plan's feature branch                                  |
| "plan-header has no branch_name field" | Branch uses non-standard name (e.g., `feature/1234`) | Manually update plan-header metadata or use standard `plnd/` pattern |
| "No PR found for branch"               | Branch exists but no PR was created                  | Push branch and create PR first                                      |

## Relationship to Fail-Open Pattern

This was previously an instance of the [fail-open pattern](../architecture/fail-open-patterns.md) with defense-in-depth. The Layer 2 fallback (pattern matching `P{issue_number}-` prefixes against git context) was removed in PR #8269. Resolution now relies on:

- **Primary mechanism**: `impl-signal started` explicitly writes `branch_name` into metadata (reliable when the full workflow runs)
- **Backup mechanism**: `plan-ref.json` provides plan-to-branch mapping independent of branch name patterns

## Related Documentation

- [Fail-Open Patterns](../architecture/fail-open-patterns.md) — Defense-in-depth design pattern
