---
title: "[Migration] ErkContext Legacy Compatibility Shims"
read_when:
  - "understanding ErkContext backwards compat for tests"
  - "seeing _LegacyIssueGatewayComposite in code"
  - "using issues or issue_link_branches parameters"
migration:
  created: 2024-12-03
  remove_when: "all tests migrated to GitHubGateway pattern"
  verification: "! grep -rE 'issues=|issue_link_branches=' --include='*.py' tests/"
---

# [Migration] ErkContext Legacy Compatibility Shims

> **TEMPORARY MIGRATION DOC**
>
> - Created: 2024-12-03
> - Remove when: All tests use `GitHubGateway` instead of legacy parameters
> - Verification: `! grep -rE 'issues=|issue_link_branches=' --include='*.py' tests/`

This document explains the temporary backwards compatibility shims in `ErkContext.for_test()` that allow old test patterns to continue working during migration.

## What Are the Shims?

`ErkContext.for_test()` accepts two legacy parameters:

```python
@classmethod
def for_test(
    cls,
    github: GitHubGateway | None = None,
    # Legacy parameters for backwards compatibility
    issues: object | None = None,  # FakeGitHubIssues
    issue_link_branches: object | None = None,  # FakeIssueLinkBranches
) -> "ErkContext":
```

When these parameters are provided, the method constructs a `GitHubGateway` internally using `_LegacyIssueGatewayComposite`.

## How They Work

### `_LegacyIssueGatewayComposite`

This internal class wraps old fakes and delegates to them:

| Operation                                                         | Delegated To            |
| ----------------------------------------------------------------- | ----------------------- |
| Issue CRUD (`create_issue`, `get_issue`, etc.)                    | `FakeGitHubIssues`      |
| Branch linking (`create_development_branch`, `get_linked_branch`) | `FakeIssueLinkBranches` |

This preserves mutation tracking on the original fake objects, so test assertions continue to work.

## Why They Exist

During the gateway refactoring, many tests used patterns like:

```python
issues = FakeGitHubIssues()
issues.set_issues([...])
ctx = env.build_context(issues=issues)

# Later in test
assert issues.created_issues == [...]  # Mutation tracking works
```

The shims allow these tests to continue working without immediate migration.

## Migration Path

### Before (legacy pattern)

```python
from erk_shared.github.issues.fake import FakeGitHubIssues

issues = FakeGitHubIssues()
issues.set_issues([test_issue])
ctx = env.build_context(issues=issues)
```

### After (new pattern)

```python
from erk_shared.github.issue.fake import FakeGitHubIssueGateway
from erk_shared.github.gateway import GitHubGateway

issue_gateway = FakeGitHubIssueGateway()
issue_gateway.set_issues([test_issue])

github = GitHubGateway(
    auth=FakeGitHubAuthGateway(),
    pr=FakeGitHubPrGateway(),
    issue=issue_gateway,
    run=FakeGitHubRunGateway(),
    workflow=FakeGitHubWorkflowGateway(),
    repo=FakeGitHubRepoGateway(),
)
ctx = env.build_context(github=github)
```

## When to Remove

The shims can be removed when:

1. All tests use `github=` parameter with `GitHubGateway`
2. No tests use `issues=` or `issue_link_branches=` parameters
3. Verification command returns exit code 0:

```bash
! grep -rE 'issues=|issue_link_branches=' --include='*.py' tests/
```

## Files Involved

- `src/erk/core/context.py` - Contains `_LegacyIssueGatewayComposite` and shim logic
- `tests/test_utils/env_helpers.py` - May have related compatibility code

## Cleanup Checklist

When removing the shims:

1. [ ] Remove `issues` and `issue_link_branches` parameters from `for_test()`
2. [ ] Delete `_LegacyIssueGatewayComposite` class
3. [ ] Update any remaining tests using old patterns
4. [ ] Delete this migration doc
