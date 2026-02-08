---
title: LBYL Gateway Pattern
read_when:
  - "implementing existence checks before gateway operations"
  - "adding LBYL validation to CLI commands"
  - "understanding why gateways have separate existence methods"
tripwires:
  - action: "calling get_X() and handling IssueNotFound sentinel inline"
    warning: "Check with X_exists() first for cleaner error messages and LBYL compliance."
  - action: "implementing idempotent operations that fail on missing resources"
    warning: "Use LBYL existence check to return early, making the operation truly idempotent."
---

# LBYL Gateway Pattern

Gateway ABCs provide separate existence-check methods (`issue_exists()`, `label_exists()`, etc.) alongside their fetch methods (`get_issue()`, `get_label()`, etc.). This enables Look Before You Leap validation at CLI boundaries.

## Why Separate Existence Methods

Gateway `get_X()` methods may return sentinels (e.g., `IssueNotFound`) or fail when resources don't exist. Without upfront existence checks, CLI commands face a choice:

1. **Handle sentinels inline** — Leads to complex control flow and cryptic error messages
2. **Catch exceptions** — Violates LBYL, creates misleading stack traces in agent sessions
3. **Check existence first** — Clean, explicit validation with user-friendly errors

The third option is erk's standard. Existence methods make LBYL practical by providing a lightweight check that avoids fetching the full resource.

## The Cross-Cutting Pattern

All gateway ABCs follow the same structure:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/issues/abc.py -->

See `GitHubIssues.issue_exists()` and `GitHubIssues.get_issue()` in the ABC for the canonical pair. The existence method returns `bool`, the fetch method returns the data type or a sentinel.

## Implementation Across Gateway Layers

The 5-layer gateway architecture implements existence checks differently at each layer:

### Real Gateway: Lightweight API Calls

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/issues/real.py, RealGitHubIssues.issue_exists -->

Real gateways use minimal API calls to check existence without fetching full resource data. For GitHub issues, this means checking the exit code of a REST API call rather than parsing the full issue JSON.

**Why not reuse `get_issue()`?** Performance. Existence checks happen in validation paths where we may not need the data. Fetching 10KB of issue JSON to answer a yes/no question wastes time and rate limits.

### Fake Gateway: Data Structure Lookup

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/issues/fake.py, FakeGitHubIssues.issue_exists -->

Fake gateways check constructor-provided test data. See `FakeGitHubIssues.issue_exists()` for the pattern — it searches the pre-configured `_issues` dict.

### Dry-Run Gateway: Delegate to Wrapped

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/issues/dry_run.py, DryRunGitHubIssues.issue_exists -->

Dry-run and printing gateways delegate existence checks to their wrapped implementations. Existence checks are read-only operations, so they execute even in dry-run mode. See `DryRunGitHubIssues.issue_exists()` — it calls `self._wrapped.issue_exists()` directly.

**Why delegate instead of no-op?** Dry-run mode validates workflows without mutating state. If a command would fail due to a missing resource, dry-run should surface that error before the user runs it for real.

## CLI Usage Pattern

<!-- Source: src/erk/cli/commands/objective/reconcile_cmd.py, reconcile_objectives -->

CLI commands follow this pattern:

1. Check existence with `issue_exists()` or equivalent
2. If missing, output user-friendly error and exit
3. Fetch resource with `get_issue()` or equivalent
4. Validate additional properties (labels, state, etc.)

See `reconcile_objectives()` in `src/erk/cli/commands/objective/reconcile_cmd.py` for the complete pattern. The existence check happens before fetch, enabling a clear "Issue not found" message instead of handling the `IssueNotFound` sentinel.

**Anti-pattern:** Calling `get_issue()` and checking for `IssueNotFound` inline. This works but produces worse error messages and violates LBYL.

**Anti-pattern:** Wrapping `get_issue()` in try/except. This creates misleading stack traces and violates erk's no-EAFP rule.

## When to Use LBYL Existence Checks

| Scenario                                    | Use LBYL?   | Reasoning                                                                 |
| ------------------------------------------- | ----------- | ------------------------------------------------------------------------- |
| Resource existence is first validation step | ✅ Yes      | Enables user-friendly "not found" errors before deeper validation         |
| Need resource data anyway                   | ⚠️ Optional | Can skip existence check and handle sentinel inline (but LBYL is cleaner) |
| Making operation idempotent                 | ✅ Yes      | Check existence, return early if missing, proceed if present              |
| Performance-critical hot path               | ❌ No       | Double API calls (exists + fetch) add latency                             |
| Operation already idempotent                | ❌ No       | Operations like `git fetch` don't fail on missing resources               |

## Implementing Idempotency with LBYL

Some operations fail when resources don't exist. LBYL existence checks make them idempotent:

**Problem:** `git branch -D feature` fails if `feature` doesn't exist
**Solution:** Check `branch_exists()` first, return early if missing, delete if present

This pattern appears in gateway methods marked "idempotent" in their docstrings. The idempotency comes from the LBYL check, not the underlying tool.

## Related Patterns

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) — 5-layer implementation pattern
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — Sentinel types like `IssueNotFound`
- [Erk Architecture Patterns](erk-architecture.md) — LBYL philosophy across the codebase
