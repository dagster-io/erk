---
title: Integration Package Inventory
read_when:
  - "understanding available integration layers"
  - "adding a new integration method"
  - "creating test doubles for external services"
---

# Integration Package Inventory

Catalog of all ABC/Fake integration packages in the erk codebase. Each integration follows the ABC/Real/Fake pattern for dependency injection and testing.

## Core Integrations

Located in `packages/erk-shared/src/erk_shared/`:

### Git (`git/`)

Git operations abstraction.

| ABC Methods                                                 | Description                         |
| ----------------------------------------------------------- | ----------------------------------- |
| `list_worktrees(repo_root)`                                 | List all worktrees for a repository |
| `add_worktree(repo_root, path, branch, ref, create_branch)` | Create a new worktree               |
| `remove_worktree(repo_root, path, force)`                   | Remove a worktree                   |
| `get_current_branch(cwd)`                                   | Get current branch name             |
| `create_branch(repo_root, name, ref)`                       | Create a new branch                 |
| `checkout_branch(cwd, branch)`                              | Checkout an existing branch         |
| `has_staged_changes(cwd)`                                   | Check if there are staged changes   |
| `detect_trunk_branch(repo_root)`                            | Detect main/master branch           |
| And 30+ more...                                             | See `git/abc.py` for full list      |

**Fake Features**: In-memory worktree state, branch tracking, configurable return values.

### GitHub (`github/`)

GitHub PR and repository operations.

| ABC Methods                                     | Description                  |
| ----------------------------------------------- | ---------------------------- |
| `get_pr(owner, repo, pr_number)`                | Get comprehensive PR details |
| `get_pr_for_branch(repo_root, branch)`          | Get PR for a branch          |
| `create_pr(repo_root, head, base, title, body)` | Create a pull request        |
| `merge_pr(repo_root, pr_number, method)`        | Merge a pull request         |
| `add_label_to_pr(repo_root, pr_number, label)`  | Add label to PR              |
| `has_pr_label(repo_root, pr_number, label)`     | Check if PR has label        |
| `get_prs_for_repo(owner, repo)`                 | Get all PRs for repository   |

**Fake Features**: In-memory PR state, configurable PR responses, label tracking, mutation tracking via `added_labels` property.

### GitHub Issues (`github/issues/`)

GitHub issue operations.

| ABC Methods                                          | Description             |
| ---------------------------------------------------- | ----------------------- |
| `get_issue(repo_root, issue_number)`                 | Get issue details       |
| `create_issue(repo_root, title, body, labels)`       | Create an issue         |
| `add_comment(repo_root, issue_number, body)`         | Add comment to issue    |
| `update_issue(repo_root, issue_number, state, body)` | Update issue state/body |

**Fake Features**: In-memory issue storage, comment tracking, state management.

## Domain Integrations

Located in `packages/erk-shared/src/erk_shared/integrations/`:

### Browser (`browser/`)

System browser launch abstraction.

| ABC Methods   | Description                                              |
| ------------- | -------------------------------------------------------- |
| `launch(url)` | Launch URL in system browser. Returns True if succeeded. |

**Fake Features**: Success mode toggle, launch call tracking via `launched_urls` property.

### Clipboard (`clipboard/`)

System clipboard abstraction.

| ABC Methods  | Description                                        |
| ------------ | -------------------------------------------------- |
| `copy(text)` | Copy text to clipboard. Returns True if succeeded. |

**Fake Features**: Success mode toggle, copy call tracking via `copied_texts` property.

### Time (`time/`)

Time operations abstraction for testable delays.

| ABC Methods      | Description                  |
| ---------------- | ---------------------------- |
| `sleep(seconds)` | Sleep for specified duration |
| `now()`          | Get current datetime         |

**Fake Features**: Fixed time injection, sleep call tracking via `sleep_calls` property, instant returns (no actual sleeping).

### Graphite (`graphite/`)

Graphite stack management operations.

| ABC Methods                                               | Description                       |
| --------------------------------------------------------- | --------------------------------- |
| `sync(repo_root, force, quiet)`                           | Run `gt sync`                     |
| `restack(repo_root, no_interactive, quiet)`               | Run `gt restack`                  |
| `squash_branch(repo_root, quiet)`                         | Squash commits on current branch  |
| `submit_stack(repo_root, publish, restack, quiet, force)` | Submit stack to create/update PRs |
| `submit_branch(repo_root, branch_name, quiet)`            | Push a single branch              |
| `track_branch(cwd, branch_name, parent_branch)`           | Track branch with Graphite        |
| `get_all_branches(git_ops, repo_root)`                    | Get all tracked branches          |
| `get_branch_stack(git_ops, repo_root, branch)`            | Get linear branch stack           |
| `get_parent_branch(git_ops, repo_root, branch)`           | Get parent branch (helper)        |
| `get_child_branches(git_ops, repo_root, branch)`          | Get child branches (helper)       |
| `check_auth_status()`                                     | Check Graphite authentication     |
| `continue_restack(repo_root, quiet)`                      | Continue in-progress restack      |

**Fake Features**: Extensive state injection (branch relationships, PR info), parent/child tracking, submit call tracking.

### Erk Worktree (`erk_wt/`)

Erk worktree kit operations.

| ABC Methods                         | Description               |
| ----------------------------------- | ------------------------- |
| `list_worktrees(cwd)`               | List erk worktrees        |
| `get_current_worktree(cwd)`         | Get current worktree info |
| `delete_worktree(cwd, name, force)` | Delete a worktree         |

**Fake Features**: In-memory worktree state, deletion tracking.

### Session Store (`extraction/claude_code_session_store/`)

Claude Code session data operations.

| ABC Methods                | Description             |
| -------------------------- | ----------------------- |
| `get_current_session_id()` | Get current session ID  |
| `get_project_dir()`        | Get project directory   |
| `list_sessions()`          | List available sessions |
| `read_session(session_id)` | Read session JSONL data |

**Fake Features**: Configurable session data, project directory injection.

### Parallel Task Runner (`parallel/`)

Parallel execution abstraction.

| ABC Methods                           | Description               |
| ------------------------------------- | ------------------------- |
| `run_in_parallel(tasks, max_workers)` | Execute tasks in parallel |

**Note**: No fake implementation - uses real ThreadPoolExecutor. Mock at task level instead.

## Implementation Layers

Each integration typically has these implementations:

| Layer    | File          | Purpose                                          |
| -------- | ------------- | ------------------------------------------------ |
| ABC      | `abc.py`      | Abstract interface definition                    |
| Real     | `real.py`     | Production implementation (subprocess/API calls) |
| Fake     | `fake.py`     | In-memory test implementation                    |
| DryRun   | `dry_run.py`  | No-op wrapper for dry-run mode (optional)        |
| Printing | `printing.py` | Logs operations before delegating (optional)     |

## Usage Pattern

```python
# Production code uses ABC types
def my_command(git: Git, github: GitHub, time: Time) -> None:
    worktrees = git.list_worktrees(repo_root)
    pr = github.get_pr_for_branch(repo_root, branch)
    time.sleep(2.0)  # Instant in tests!

# Tests inject fakes
def test_my_command() -> None:
    fake_git = FakeGit(worktrees=[...])
    fake_github = FakeGitHub(prs={...})
    fake_time = FakeTime()

    my_command(fake_git, fake_github, fake_time)

    assert fake_time.sleep_calls == [2.0]
```

## Adding New Integrations

When adding a new integration:

1. Create `abc.py` with interface definition
2. Create `real.py` with production implementation
3. Create `fake.py` with in-memory test implementation
4. Create `dry_run.py` if operations are destructive (optional)
5. Add to `__init__.py` with re-exports
6. Update `ErkContext` to include new integration

**Related**: [Erk Architecture Patterns](erk-architecture.md#integration-layer-directory-structure)
