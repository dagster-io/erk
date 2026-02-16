---
title: PR Discovery Strategies for Plans
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
read_when:
  - "finding the PR associated with an erk plan issue"
  - "debugging why get-pr-for-plan returns no-branch-in-plan"
  - "understanding how erk learn finds PRs"
  - "working with plan-header branch_name field"
tripwires:
  - action: "assuming branch_name is always present in plan-header metadata"
    warning: "branch_name is null until Phase 2 (plan submit). Check the plan metadata field lifecycle in lifecycle.md."
  - action: "using issue timeline API as the primary PR lookup path"
    warning: "The primary path is branch_name from plan-header → get_pr_for_branch(). Timeline API is a separate strategy for when branch_name is unavailable."
---

# PR Discovery Strategies for Plans

Finding the PR associated with a plan issue is a cross-cutting concern that spans multiple commands (`get-pr-for-plan`, `trigger-async-learn`, `plan checkout`, `plan close`). Two fundamentally different strategies exist, chosen based on what metadata is available.

## Why Two Strategies Exist

Plan metadata accumulates progressively through the lifecycle. The `branch_name` field — the simplest path to PR discovery — doesn't exist until Phase 2 (submission). Commands that run before submission, or that process older plans with incomplete metadata, need an alternative path.

| Available Data | Strategy            | Used By                                                 |
| -------------- | ------------------- | ------------------------------------------------------- |
| `branch_name`  | Branch → PR lookup  | `get-pr-for-plan`, `trigger-async-learn`, land, submit  |
| `issue_number` | Issue timeline → PR | `get-issue-timeline-prs`, `plan checkout`, `plan close` |

## Strategy 1: Branch-Based Lookup (Primary)

The plan-header metadata block contains a `branch_name` field populated during `erk plan submit`. Given a branch name, the GitHub gateway's `get_pr_for_branch()` method returns PR details directly.

<!-- Source: src/erk/cli/commands/exec/scripts/get_pr_for_plan.py, get_pr_for_plan -->

See `get_pr_for_plan()` in `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py` for the canonical implementation. This command also includes a **git context fallback**: if `branch_name` is null in metadata but the current branch matches the `P{issue_number}-` naming convention, it infers the branch from git state. This handles cases where `impl-signal` failed to write the metadata.

**Why branch-first**: Branch-to-PR is a deterministic 1:1 lookup via the GitHub API. Issue timeline depends on cross-references being recorded, which requires specific keywords in the PR body.

## Strategy 2: Issue Timeline Lookup (Fallback)

When `branch_name` is unavailable, the GitHub issues timeline API finds PRs that cross-reference the issue. This uses the `get_prs_referencing_issue()` gateway method, which filters timeline events for `cross-referenced` entries.

<!-- Source: src/erk/cli/commands/exec/scripts/get_issue_timeline_prs.py, get_issue_timeline_prs -->

See `get_issue_timeline_prs()` in `src/erk/cli/commands/exec/scripts/get_issue_timeline_prs.py`.

**Limitation**: Only works when the PR body contains "Closes #N" or similar GitHub keywords. PRs created without issue-linking keywords won't appear in timeline results. This is why branch-based lookup is preferred.

## The `trigger-async-learn` Composition

The `erk learn` workflow composes both strategies. It uses the branch-based path (via `_get_pr_for_plan_direct()`) but treats PR absence as non-fatal — learn can proceed without review comments if no PR is found.

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, _get_pr_for_plan_direct -->

See `_get_pr_for_plan_direct()` in `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`. This is an inline version of `get-pr-for-plan` logic that avoids subprocess overhead by calling gateways directly.

## Anti-Patterns

**Assuming `get-pr-for-plan` always succeeds**: The command returns structured error codes (`no-branch-in-plan`, `no-pr-for-branch`) that callers must handle. Plans in Phase 1 (created but not submitted) will always return `no-branch-in-plan`.

**Using git history search as a discovery strategy**: The current codebase does not use `git log --grep` for PR discovery. Earlier designs considered it, but it was never implemented because branch naming conventions make branch-based lookup reliable.

**Skipping PR validation after discovery**: A PR existing for a branch doesn't mean it contains the implementation. A queued plan has a PR with only `.worker-impl/` files. Check for changes outside `.worker-impl/` to confirm actual implementation (see lifecycle.md, "Detecting Queued vs Implemented Plans").

## Related Documentation

- [Plan Lifecycle](lifecycle.md) — Metadata field population timeline and Phase definitions
- [Session Management](../cli/session-management.md) — Session metadata structure
- [GitHub CLI Limits](../architecture/github-cli-limits.md) — REST API alternatives for large PRs
