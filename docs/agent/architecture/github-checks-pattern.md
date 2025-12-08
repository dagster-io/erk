---
title: GitHubChecks Pattern
read_when:
  - "calling GitHub API in kit commands"
  - "handling GitHub operation failures"
  - "using NonIdealState with GitHub operations"
---

# GitHubChecks Pattern

Static class that wraps GitHub operations to return `T | NonIdealState` instead of throwing.

## Location

`packages/dot-agent-kit/src/dot_agent_kit/non_ideal_state.py`

## Available Methods

```python
class GitHubChecks:
    @staticmethod
    def branch(branch: str | None) -> str | BranchDetectionFailed:
        """Check if branch was detected."""

    @staticmethod
    def pr_for_branch(github, repo_root, branch) -> PRDetails | NoPRForBranch:
        """Look up PR for branch."""

    @staticmethod
    def pr_by_number(github, repo_root, pr_number) -> PRDetails | PRNotFoundError:
        """Look up PR by number."""

    @staticmethod
    def add_reaction(github_issues, repo_root, comment_id, reaction) -> None | GitHubAPIFailed:
        """Add reaction to a comment."""

    @staticmethod
    def issue_comments(github_issues, repo_root, issue_number) -> list | GitHubAPIFailed:
        """Get issue/PR discussion comments."""
```

## Usage in Kit Commands

```python
from dot_agent_kit.cli_result import exit_with_error
from dot_agent_kit.non_ideal_state import (
    GitHubChecks, BranchDetectionFailed, NoPRForBranch
)

# Chain of checks with early exit on error
branch_result = GitHubChecks.branch(get_current_branch(ctx))
if isinstance(branch_result, BranchDetectionFailed):
    exit_with_error(branch_result.error_type, branch_result.message)
branch = branch_result

pr_result = GitHubChecks.pr_for_branch(github, repo_root, branch)
if isinstance(pr_result, NoPRForBranch):
    exit_with_error(pr_result.error_type, pr_result.message)
pr_details = pr_result
```

## Design Principles

1. **Never throws** - All errors returned as NonIdealState
2. **Thin wrapper** - Minimal logic, just error type conversion
3. **Composable** - Results can be chained with isinstance checks
