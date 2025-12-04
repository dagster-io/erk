---
title: "[Migration] GitHub Gateway Refactoring"
read_when:
  - "migrating code from old GitHub/FakeGitHub pattern"
  - "updating test imports for GitHub gateways"
migration:
  created: 2024-12-03
  remove_when: "all old GitHub/FakeGitHub imports are removed"
  verification: "! grep -rE 'from.*(FakeGitHub|RealGitHub)[^G]' --include='*.py' ."
---

# [Migration] GitHub Gateway Refactoring

> **TEMPORARY MIGRATION DOC**
>
> - Created: 2024-12-03
> - Remove when: All code migrated to new `GitHubGateway` composite pattern
> - Verification: `! grep -rE 'from.*(FakeGitHub|RealGitHub)[^G]' --include='*.py' .`

This document covers migrating from the old mega-class `GitHub`/`FakeGitHub` pattern to the new composite `GitHubGateway` with sub-gateways.

## Migration Summary

| Old Pattern                 | New Pattern                     |
| --------------------------- | ------------------------------- |
| `GitHub` ABC                | `GitHubGateway` composite       |
| `FakeGitHub`                | `FakeGitHub*Gateway` per domain |
| `ctx.github.method()`       | `ctx.github.sub.method()`       |
| `github_issues` field       | `github.issue` sub-gateway      |
| `github_admin` field        | `github.workflow` sub-gateway   |
| `issue_link_branches` field | `github.issue` sub-gateway      |

## Import Changes

### Old Imports (to replace)

```python
# OLD - Remove these
from tests.fakes.github import FakeGitHub
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
```

### New Imports

```python
# NEW - Use these
from erk_shared.github.gateway import GitHubGateway, create_fake_github_gateway
from erk_shared.github.auth.fake import FakeGitHubAuthGateway
from erk_shared.github.pr.fake import FakeGitHubPrGateway
from erk_shared.github.issue.fake import FakeGitHubIssueGateway
from erk_shared.github.run.fake import FakeGitHubRunGateway
from erk_shared.github.workflow.fake import FakeGitHubWorkflowGateway
from erk_shared.github.repo.fake import FakeGitHubRepoGateway
```

## Test Migration Patterns

### Simple Tests (no custom behavior)

**Before:**

```python
from tests.fakes.github import FakeGitHub

def test_something():
    ctx = env.build_context(github=FakeGitHub())
```

**After:**

```python
from erk_shared.github.gateway import create_fake_github_gateway

def test_something():
    ctx = env.build_context(github=create_fake_github_gateway())
```

### Tests with Custom Fake Behavior

**Before:**

```python
github = FakeGitHub()
github.set_pr_status("my-branch", "open")
ctx = env.build_context(github=github)
```

**After:**

```python
from erk_shared.github.pr.fake import FakeGitHubPrGateway

pr_gateway = FakeGitHubPrGateway()
pr_gateway.set_pr_status("my-branch", "open")

github = GitHubGateway(
    auth=FakeGitHubAuthGateway(),
    pr=pr_gateway,
    issue=FakeGitHubIssueGateway(),
    run=FakeGitHubRunGateway(),
    workflow=FakeGitHubWorkflowGateway(),
    repo=FakeGitHubRepoGateway(),
)
ctx = env.build_context(github=github)
```

### Helper Function Pattern

For test files with many tests needing custom gateways, create a local helper:

```python
def _create_github_gateway(
    pr: FakeGitHubPrGateway | None = None,
    issue: FakeGitHubIssueGateway | None = None,
) -> GitHubGateway:
    """Create GitHubGateway with optional custom sub-gateways."""
    return GitHubGateway(
        auth=FakeGitHubAuthGateway(),
        pr=pr or FakeGitHubPrGateway(),
        issue=issue or FakeGitHubIssueGateway(),
        run=FakeGitHubRunGateway(),
        workflow=FakeGitHubWorkflowGateway(),
        repo=FakeGitHubRepoGateway(),
    )
```

## Call Site Changes

### PR Operations

```python
# Before
ctx.github.create_pr(...)
ctx.github.get_pr_status(...)

# After
ctx.github.pr.create_pr(...)
ctx.github.pr.get_pr_status(...)
```

### Issue Operations

```python
# Before
ctx.github_issues.create_issue(...)
ctx.issue_link_branches.create_development_branch(...)

# After
ctx.github.issue.create_issue(...)
ctx.github.issue.create_development_branch(...)
```

### Workflow Operations

```python
# Before
ctx.github_admin.get_workflow_permissions(...)
ctx.github.trigger_workflow(...)

# After
ctx.github.workflow.get_workflow_permissions(...)
ctx.github.workflow.trigger_workflow(...)
```

## Common Pitfalls

### 1. Forgetting Sub-Gateway Prefix

```python
# WRONG - method doesn't exist on GitHubGateway
ctx.github.create_pr(...)

# RIGHT - use the sub-gateway
ctx.github.pr.create_pr(...)
```

### 2. Using Old Issue Gateway

```python
# WRONG - old separate gateway
ctx.github_issues.create_issue(...)

# RIGHT - issue is now a sub-gateway
ctx.github.issue.create_issue(...)
```

### 3. Import Path Confusion

```python
# WRONG - old path (may still exist during migration)
from erk_shared.github.issues.fake import FakeGitHubIssues

# RIGHT - new path
from erk_shared.github.issue.fake import FakeGitHubIssueGateway
```

Note: The directory is `issue/` (singular) not `issues/` (plural).

## Verification

Run this command to check migration progress:

```bash
# Should return exit code 0 (no matches) when migration complete
! grep -rE 'from.*(FakeGitHub|RealGitHub)[^G]' --include='*.py' .
```

This grep pattern matches old `FakeGitHub`/`RealGitHub` imports but excludes new `FakeGitHub*Gateway`/`RealGitHub*Gateway` imports.
