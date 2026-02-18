---
title: Test Context Composition
read_when:
  - "using build_workspace_test_context with custom fakes"
  - "debugging invisible metadata writes in tests"
  - "understanding issues_explicitly_passed flag"
tripwires:
  - action: "creating custom FakeGitHubIssues without passing to test context builder"
    warning: "Always pass issues=issues to build_workspace_test_context when using custom FakeGitHubIssues. Without it, plan_backend operates on a different instance and metadata writes are invisible."
---

# Test Context Composition

When building test contexts with custom fakes, the composition matters — particularly for `FakeGitHubIssues` instances that are shared across multiple consumers.

## The Shared Instance Problem

`build_workspace_test_context()` creates a default `FakeGitHubIssues` if none is passed. If you create your own `FakeGitHubIssues` but don't pass it to the context builder, two separate instances exist:

1. Your instance (which you assert against)
2. The context builder's internal instance (which `plan_backend` uses)

Metadata writes through `plan_backend` go to instance #2, invisible to your assertions on instance #1.

## Correct Pattern

```python
def test_metadata_is_written(env: ErkInMemEnv) -> None:
    issues = FakeGitHubIssues(issues={42: IssueInfo(
        number=42, title="Plan", body="# Plan\n\nContent", ...
    )})

    ctx = build_workspace_test_context(
        env, issues=issues,  # Share the instance
    )

    # Now plan_backend and direct assertions use the same instance
    ctx.plan_backend.update_metadata(repo_root, "42", {"key": "value"})
    assert any("key" in body for _, body in issues.updated_bodies)
```

## When issues is Auto-Created vs Explicitly Shared

| Scenario | issues parameter   | Result                                             |
| -------- | ------------------ | -------------------------------------------------- |
| Default  | omitted            | Context creates its own FakeGitHubIssues           |
| Shared   | `issues=my_issues` | Context uses your instance; plan_backend shares it |

## Related Documentation

- [CLI Testing Patterns](../testing/cli-testing.md) — Pattern 6: FakeGitHub with Shared FakeGitHubIssues
- [FakeGitHubIssues Testing](../testing/fake-github-testing.md) — Dual-comment parameters and context wiring
