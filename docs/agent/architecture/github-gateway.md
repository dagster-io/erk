---
title: GitHub Gateway Architecture
read_when:
  - "working with GitHub API operations"
  - "understanding GitHubGateway composite pattern"
  - "adding new GitHub functionality"
  - "writing tests that use GitHub"
---

# GitHub Gateway Architecture

The GitHub integration uses a **composite gateway pattern** that organizes operations into logical sub-gateways aligned with the `gh` CLI command hierarchy.

## Overview

```
GitHubGateway (composite)
├── auth      → GitHubAuthGateway      (authentication, username)
├── pr        → GitHubPrGateway        (pull requests, mergeability, CI status)
├── issue     → GitHubIssueGateway     (issues, labels, comments, dev branches)
├── run       → GitHubRunGateway       (workflow runs, logs)
├── workflow  → GitHubWorkflowGateway  (triggering workflows, permissions)
└── repo      → GitHubRepoGateway      (repository info)
```

## Access Pattern

Access GitHub operations through the `ctx.github` composite, then the sub-gateway:

```python
# Authentication
ctx.github.auth.check_auth_status()
ctx.github.auth.get_current_username()

# Pull Requests
ctx.github.pr.create_pr(location, title, body, base_branch, head_branch, draft)
ctx.github.pr.get_pr_status(location, branch)
ctx.github.pr.merge_pr(location, branch)

# Issues
ctx.github.issue.create_issue(location, title, body, labels)
ctx.github.issue.get_issue(location, issue_number)
ctx.github.issue.add_comment(location, issue_number, body)

# Workflow Runs
ctx.github.run.list_workflow_runs(location, workflow_name, branch)
ctx.github.run.get_run_logs(location, run_id)

# Workflows
ctx.github.workflow.trigger_workflow(location, workflow_name, ref, inputs)
ctx.github.workflow.get_workflow_permissions(location)

# Repository
ctx.github.repo.get_repo_info(location)
```

## Sub-Gateway Responsibilities

### `GitHubAuthGateway`

Authentication and identity operations:

- `check_auth_status()` - Verify gh CLI is authenticated
- `get_current_username()` - Get authenticated user's username

### `GitHubPrGateway`

Pull request lifecycle and queries:

- Create, close, merge PRs
- Query PR status, mergeability, CI status
- Update PR title, body, base branch
- Batch operations for PR enrichment

### `GitHubIssueGateway`

Issue management and development branches:

- Create, close, update issues
- Manage labels and comments
- Create development branches linked to issues
- Query linked branches

### `GitHubRunGateway`

Workflow run monitoring:

- List and query workflow runs
- Get run logs and status
- Poll for run completion
- Batch queries by branch or node ID

### `GitHubWorkflowGateway`

Workflow triggering and permissions:

- Trigger workflow dispatch events
- Query and set workflow permissions

### `GitHubRepoGateway`

Repository information:

- Get repository metadata

## Testing Pattern

Use `create_fake_github_gateway()` for tests with default fakes:

```python
from erk_shared.github.gateway import create_fake_github_gateway

def test_something():
    github = create_fake_github_gateway()
    ctx = env.build_context(github=github)
```

For custom fake behavior, construct the gateway with specific fakes:

```python
from erk_shared.github.gateway import GitHubGateway
from erk_shared.github.auth.fake import FakeGitHubAuthGateway
from erk_shared.github.pr.fake import FakeGitHubPrGateway
from erk_shared.github.issue.fake import FakeGitHubIssueGateway
from erk_shared.github.run.fake import FakeGitHubRunGateway
from erk_shared.github.workflow.fake import FakeGitHubWorkflowGateway
from erk_shared.github.repo.fake import FakeGitHubRepoGateway

def test_with_custom_pr_gateway():
    custom_pr = FakeGitHubPrGateway()
    custom_pr.set_pr_status("my-branch", "open")

    github = GitHubGateway(
        auth=FakeGitHubAuthGateway(),
        pr=custom_pr,
        issue=FakeGitHubIssueGateway(),
        run=FakeGitHubRunGateway(),
        workflow=FakeGitHubWorkflowGateway(),
        repo=FakeGitHubRepoGateway(),
    )
    ctx = env.build_context(github=github)
```

Helper function pattern for tests needing custom gateways:

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

## Directory Structure

```
erk_shared/github/
├── __init__.py              # Exports GitHubGateway + sub-gateways
├── gateway.py               # GitHubGateway composite class
├── types.py                 # Shared types
├── auth/
│   ├── abc.py               # GitHubAuthGateway ABC
│   ├── real.py              # RealGitHubAuthGateway
│   └── fake.py              # FakeGitHubAuthGateway
├── pr/
│   ├── abc.py               # GitHubPrGateway ABC
│   ├── real.py              # RealGitHubPrGateway
│   └── fake.py              # FakeGitHubPrGateway
├── issue/
│   ├── abc.py               # GitHubIssueGateway ABC
│   ├── real.py              # RealGitHubIssueGateway
│   ├── fake.py              # FakeGitHubIssueGateway
│   └── types.py             # Issue-specific types
├── run/
│   ├── abc.py               # GitHubRunGateway ABC
│   ├── real.py              # RealGitHubRunGateway
│   └── fake.py              # FakeGitHubRunGateway
├── workflow/
│   ├── abc.py               # GitHubWorkflowGateway ABC
│   ├── real.py              # RealGitHubWorkflowGateway
│   └── fake.py              # FakeGitHubWorkflowGateway
└── repo/
    ├── abc.py               # GitHubRepoGateway ABC
    ├── real.py              # RealGitHubRepoGateway
    └── fake.py              # FakeGitHubRepoGateway
```

## Design Rationale

### Why Composite Pattern?

1. **Aligned with `gh` CLI** - The sub-gateway names match `gh` subcommands (`gh pr`, `gh issue`, `gh run`, etc.)
2. **Separation of Concerns** - Each sub-gateway has a focused responsibility
3. **Testability** - Easy to inject custom fakes for specific sub-gateways
4. **Discoverability** - IDE autocomplete guides developers to the right operations

### Why Frozen Dataclass?

The `GitHubGateway` is a frozen dataclass because:

- Sub-gateways are set at construction and never change
- Immutability prevents accidental mutation during request handling
- Clear constructor-based dependency injection

## See Also

- [protocol-vs-abc.md](protocol-vs-abc.md) - When to use Protocol vs ABC
- [subprocess-wrappers.md](subprocess-wrappers.md) - How real gateways call `gh` CLI
