---
title: GitHub Actions Label Queries
read_when:
  - "checking PR labels in GitHub Actions workflows"
  - "working with push event workflows"
  - "implementing CI gating based on PR labels"
tripwires:
  - score: 6
    action: "Label checks in push event workflows"
    warning: "Job-level label access via github.event.pull_request.labels is ONLY available in pull_request events, NOT push events. For push events, you must use step-level GitHub API queries with gh cli or REST API."
    context: "The asymmetry exists because push events don't have github.event.pull_request in their context. Defense-in-depth: Keep job-level checks for pull_request events (fast path), add step-level API queries for push events (required path)."
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# GitHub Actions Label Queries

## The Asymmetry Problem

GitHub Actions workflows face a fundamental asymmetry in how PR labels are accessed:

**pull_request events**: The `github.event.pull_request` context is populated, so labels are available via `github.event.pull_request.labels.*.name` at job evaluation time (before any steps run).

**push events**: The `github.event.pull_request` context does **not exist**. There is no PR context at job evaluation time, even if the push is to a branch with an open PR.

This asymmetry is architectural, not a bug. Push events are branch operations; GitHub Actions doesn't implicitly resolve "what PR is this branch associated with?" until you ask via the API.

## Why This Matters for CI Gating

Label-based gating (like "skip autofix on plan review PRs") must work for both event types:

- Users can trigger CI via **pull_request events** (opening/updating PR in GitHub UI)
- Users can trigger CI via **push events** (git push from local terminal)

If your workflow only handles pull_request events, local pushes will bypass your gating logic.

## Defense-in-Depth Pattern

The solution is two-layered label checking:

**Layer 1: Job-level condition** (pull_request events only)

- Fast path: GitHub evaluates the condition before allocating a runner
- Prevents job execution entirely if label check fails
- Cannot work for push events (no PR context available)

**Layer 2: Step-level API query** (all events)

- Required path for push events: Query GitHub API to discover PR and fetch labels
- Safety net for pull_request events: Redundant check, but provides defense-in-depth
- Runs after checkout, so it sees current repository state

<!-- Source: .github/workflows/ci.yml, autofix job -->

See the `autofix` job in `.github/workflows/ci.yml` for the canonical implementation. Key steps:

1. **Discover PR step**: For pull_request events, use `github.event.pull_request.number`. For push events, query `gh api repos/.../pulls` to find open PRs for the current branch.

2. **Check label step**: Query `gh api repos/.../pulls/{pr_number}` to fetch labels array, then grep for the target label.

3. **Consolidate conditions step**: Combine all skip conditions (has_pr, is_fork, has_plan_review_label, has_impl_folder) into a single boolean output.

4. **Gate all subsequent steps**: Check `steps.should-autofix.outputs.run == 'true'` instead of repeating complex conditions.

## Why Not Job-Level Only?

**Q: Why not skip job-level conditions and use only step-level API queries?**

A: Job-level conditions are evaluated before runner allocation. If a pull_request event has the `erk-plan-review` label, the job-level condition prevents GitHub from even starting a runner, saving CI minutes and reducing queue pressure.

Step-level queries require a runner to be allocated, checkout to complete, and API calls to execute. This wastes resources for cases that could be rejected earlier.

The defense-in-depth pattern uses the fast path when available (job-level for pull_request) and falls back to the required path when necessary (step-level for push).

## API Query Pattern

For push events, PR discovery is a two-step process:

1. **Find PR number**: `gh api repos/{repo}/pulls --jq ".[] | select(.head.ref == \"{branch}\" and .state == \"open\") | .number"`
2. **Fetch labels**: `gh api repos/{repo}/pulls/{pr_number} --jq '[.labels[].name] | join(",")'`

Use `gh api` instead of `gh pr view` because the latter requires being in a repository checkout with the PR branch, while `gh api` works from any checkout state.

## Anti-Pattern: Job-Level Push Event Checks

**WRONG:**

```yaml
autofix:
  if: |
    github.event_name == 'push' &&
    !contains(github.event.pull_request.labels.*.name, 'erk-plan-review')
```

This condition will always evaluate to true for push events because `github.event.pull_request` is null. The `contains()` function returns false when the array is empty/null, so the negation becomes true.

The job will run even when the PR has the label, bypassing your gating logic.

## Related Patterns

- [Workflow Gating Patterns](workflow-gating-patterns.md) - Autofix safety pattern
- [CI Tripwires](tripwires.md) - All CI-related tripwires
