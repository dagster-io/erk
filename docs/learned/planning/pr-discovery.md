---
title: PR Discovery Strategies for Plans
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
read_when:
  - "finding the PR associated with an erk plan"
  - "debugging why PR lookup returns no-branch-in-plan"
  - "understanding how erk learn finds PRs"
  - "working with plan-header branch_name field"
tripwires:
  - action: "assuming branch_name is always present in plan-header metadata"
    warning: "branch_name is null until Phase 2 (pr dispatch). Check the plan metadata field lifecycle in lifecycle.md."
  - action: "looking for alternative PR lookup paths beyond branch-based"
    warning: "Branch-based lookup via get_pr_for_branch() is the only PR discovery strategy. The issue timeline API was removed."
---

# PR Discovery Strategies for Plans

Finding the PR associated with a plan is a cross-cutting concern that spans multiple commands (`get-plan-info`, `trigger-async-learn`, `erk pr co`, `erk pr close`). The strategy depends on what metadata is available.

## Discovery Strategy

Plan metadata accumulates progressively through the lifecycle. The `branch_name` field doesn't exist until Phase 2 (submission). Commands that run before submission will not find a PR.

| Available Data | Strategy           | Used By                                                |
| -------------- | ------------------ | ------------------------------------------------------ |
| `branch_name`  | Branch → PR lookup | `get-plan-info`, `trigger-async-learn`, land, dispatch |

## Branch-Based Lookup

The plan-header metadata block contains a `branch_name` field populated during `erk pr dispatch`. Given a branch name, the GitHub gateway's `get_pr_for_branch()` method returns PR details directly.

The `get-plan-info` command exposes `head_ref_name` and `base_ref_name` from plan metadata, providing branch information for PR discovery.

**Why branch-based**: Branch-to-PR is a deterministic 1:1 lookup via the GitHub API.

## The `trigger-async-learn` Composition

The `erk learn` workflow uses the branch-based path but treats PR absence as non-fatal — learn can proceed without review comments if no PR is found.

## Anti-Patterns

**Assuming PR lookup always succeeds**: Plans in Phase 1 (created but not submitted) will not have branch metadata. Callers must handle the absence case.

**Using git history search as a discovery strategy**: The current codebase does not use `git log --grep` for PR discovery. Earlier designs considered it, but it was never implemented because branch naming conventions make branch-based lookup reliable.

**Skipping PR validation after discovery**: A PR existing for a branch doesn't mean it contains the implementation. A queued plan has a PR with only `.erk/impl-context/` files. Check for changes outside `.erk/impl-context/` to confirm actual implementation (see lifecycle.md, "Detecting Queued vs Implemented Plans").

## Related Documentation

- [Plan Lifecycle](lifecycle.md) — Metadata field population timeline and Phase definitions
- [Session Management](../cli/session-management.md) — Session metadata structure
- [GitHub CLI Limits](../architecture/github-cli-limits.md) — REST API alternatives for large PRs
