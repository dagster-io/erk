---
title: FakeGitHub API Reference
read_when:
  - "writing tests that need fake GitHub PR or issue data"
  - "understanding FakeGitHub.create_pr() auto-registration"
  - "using mutation tracking in GitHub fake tests"
tripwires:
  - action: "creating a FakeGitHub PR without checking auto-registration in _pr_details"
    warning: "FakeGitHub.create_pr() auto-registers the PR in _pr_details. Manually adding to _pr_details after create_pr() causes duplicates."
  - action: "using context_for_test without matching parameter names to the current API"
    warning: "context_for_test() parameter names evolve. Check the current function signature before adding new parameters."
---

# FakeGitHub API Reference

Reference for the FakeGitHub test double used throughout erk's test suite. Covers auto-registration behavior, mutation tracking, and common patterns.

## FakeGitHub.create_pr() Auto-Registration

When `FakeGitHub.create_pr()` is called, it automatically:

1. Creates the PR record
2. Registers it in `_pr_details` for subsequent `get_pr_details()` calls
3. Adds it to the open PRs list

Do NOT manually add to `_pr_details` after calling `create_pr()` — this causes duplicate entries.

## Mutation Tracking API

FakeGitHub tracks all mutations for test assertions:

| Property               | Tracks                         | Tuple Format              |
| ---------------------- | ------------------------------ | ------------------------- |
| `created_prs`          | PRs created via create_pr()    | (title, body, base, head) |
| `added_labels`         | Labels added to issues/PRs     | (number, label)           |
| `removed_labels`       | Labels removed from issues/PRs | (number, label)           |
| `posted_comments`      | Comments posted to issues/PRs  | (number, body)            |
| `updated_issue_bodies` | Issue body updates             | (number, new_body)        |

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
# Create a PR with specific details
fake_github.add_pr_details(
    pr_number=42,
    title="My PR",
    body="PR body content",
)

# Set up issue with labels
fake_issues.add_issue(
    number=100,
    title="Plan issue",
    labels=["erk-plan", "erk-planned-pr"],
)
```

## Related Documentation

- [Backend Testing Composition](backend-testing-composition.md) — Real backend + fake gateway testing
- [FakeGitHub Mutation Tracking](fake-github-mutation-tracking.md) — Detailed mutation tracking patterns
- [FakeGitHubIssues Dual-Comment Parameters](fake-github-testing.md) — Issue vs PR comment routing
