---
title: Backend Testing Composition
read_when:
  - "testing code that uses PlanBackend"
  - "deciding whether to fake a backend or gateway"
  - "writing tests for exec scripts with backend operations"
tripwires:
  - action: "creating a FakePlanBackend for testing caller code"
    warning: "Use real backend + fake gateway instead. FakeGitHubIssues injected into GitHubPlanStore. Fake backends are only for validating ABC contract across providers."
---

# Backend Testing Composition

Pattern for testing code that uses Backend ABCs. The key insight: inject fake gateways into real backends, rather than creating fake backends.

## Core Pattern

```python
# Correct: real backend with fake gateway
fake_issues = FakeGitHubIssues(issues={123: issue})
backend = GitHubPlanStore(fake_issues)

# Wrong: fake backend for testing callers
fake_backend = FakePlanBackend()  # Only for ABC contract tests
```

### Why Real Backend + Fake Gateway

Backends contain business logic (metadata block formatting, comment rendering, event composition). Faking the backend bypasses this logic, making tests less valuable. By using the real backend with a fake gateway:

1. Business logic in the backend is exercised
2. Gateway interactions (API calls) are captured by the fake
3. Tests verify the full call chain from caller -> backend -> gateway

## Example: Testing impl_signal.py

From `tests/unit/cli/commands/exec/scripts/test_impl_signal.py`:

See `test_started_posts_comment_and_updates_metadata` in
[`tests/unit/cli/commands/exec/scripts/test_impl_signal.py`](../../../tests/unit/cli/commands/exec/scripts/test_impl_signal.py)
for the full test. The key elements:

- Creates a `FakeGitHubIssues` with a test issue
- Invokes `impl_signal` via `CliRunner` with `ErkContext.for_test(github_issues=fake_issues)`
- Asserts on `fake_issues.added_comments` and `fake_issues.updated_bodies`

## When to Use Fake Backends

Fake backends are appropriate only for validating the ABC contract itself across different providers. For example, ensuring both `GitHubPlanStore` and a hypothetical `JiraPlanStore` implement the same interface correctly.

## Decision Table

| Testing Scenario                | Approach                    |
| ------------------------------- | --------------------------- |
| Caller uses backend methods     | Real backend + fake gateway |
| Backend ABC contract validation | Fake backend                |
| Gateway method behavior         | Fake gateway directly       |

## Assertion Pattern

Assert on fake gateway mutation tracking properties:

| Property                     | What It Tracks                                    |
| ---------------------------- | ------------------------------------------------- |
| `fake_issues.added_comments` | List of `(issue_number, body, comment_id)` tuples |
| `fake_issues.updated_bodies` | List of `(issue_number, body)` tuples             |
| `fake_issues.added_labels`   | List of `(issue_number, label)` tuples            |

## Related Documentation

- [Gateway vs Backend](../architecture/gateway-vs-backend.md) - Architecture distinction
- [PlanBackend Migration](../architecture/plan-backend-migration.md) - Migration pattern
- [Erk Test Reference](testing.md) - General testing patterns
