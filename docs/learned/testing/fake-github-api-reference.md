---
title: FakeLocalGitHub API Reference
read_when:
  - "writing tests that need fake GitHub PR or issue data"
  - "understanding FakeLocalGitHub.create_pr() auto-registration"
  - "using mutation tracking in LocalGitHub fake tests"
tripwires:
  - action: "creating a FakeLocalGitHub PR without checking auto-registration in _pr_details"
    warning: "FakeLocalGitHub.create_pr() auto-registers the PR in _pr_details. Manually adding to _pr_details after create_pr() causes duplicates."
  - action: "using context_for_test without matching parameter names to the current API"
    warning: "context_for_test() parameter names evolve. Check the current function signature before adding new parameters."
---

# FakeLocalGitHub API Reference

Reference for the FakeLocalGitHub test double used throughout erk's test suite. Covers auto-registration behavior, mutation tracking, and common patterns.

## FakeLocalGitHub.create_pr() Auto-Registration

When `FakeLocalGitHub.create_pr()` is called, it automatically:

1. Creates the PR record
2. Registers it in `_pr_details` for subsequent `get_pr_details()` calls
3. Adds it to the open PRs list

Do NOT manually add to `_pr_details` after calling `create_pr()` — this causes duplicate entries.

## Mutation Tracking API

FakeLocalGitHub tracks all mutations for test assertions:

| Property                  | Tracks                           | Format                             |
| ------------------------- | -------------------------------- | ---------------------------------- |
| `created_prs`             | PRs created via create_pr()      | (branch, title, body, base, draft) |
| `added_labels`            | Labels added to issues/PRs       | (number, label)                    |
| `merged_prs`              | PR numbers that were merged      | list[int]                          |
| `closed_prs`              | PR numbers that were closed      | list[int]                          |
| `updated_pr_bases`        | PR base branch updates           | (number, base)                     |
| `updated_pr_bodies`       | PR body updates                  | (number, body)                     |
| `updated_pr_titles`       | PR title updates                 | (number, title)                    |
| `triggered_workflows`     | Workflow dispatch triggers       | (workflow, dict[str, str])         |
| `resolved_thread_ids`     | Resolved review thread IDs       | set[str]                           |
| `thread_replies`          | Replies posted to review threads | (thread_id, body)                  |
| `pr_comments`             | Comments posted to PRs           | (number, body)                     |
| `deleted_remote_branches` | Remote branches deleted          | list[str]                          |

Access via properties that return copies (not the internal mutable lists).

## context_for_test() Patterns

The `context_for_test()` standalone function creates an `ErkContext` with configurable fakes:

```python
ctx = context_for_test(
    cwd=tmp_path,
    github=fake_github,
    git=fake_git,
)
```

Parameter names match the `ErkContext` field names. Check the current signature in `packages/erk-shared/src/erk_shared/context/` before use.

## Test Helper Function Patterns

Common patterns for setting up test data:

```python
# Configure PR details via constructor
fake_github = FakeLocalGitHub(
    pr_details={42: PRDetails(number=42, title="My PR", body="PR body content")},
)

# Configure issues via constructor
fake_issues = FakeGitHubIssues(
    issues={100: IssueInfo(number=100, title="Example plan", labels=["erk-plan", "erk-planned-pr"])},
)
```

## Related Documentation

- [Backend Testing Composition](backend-testing-composition.md) — Real backend + fake gateway testing
- [FakeLocalGitHub Mutation Tracking](fake-github-mutation-tracking.md) — Detailed mutation tracking patterns
- [FakeGitHubIssues Dual-Comment Parameters](fake-github-testing.md) — Issue vs PR comment routing
