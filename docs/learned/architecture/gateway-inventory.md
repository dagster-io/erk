---
title: Gateway Inventory
read_when:
  - "understanding available gateways"
  - "adding a new gateway"
  - "creating test doubles for external services"
---

# Gateway Inventory

Catalog of all ABC/Fake gateway packages in the erk codebase. Each gateway follows the ABC/Real/Fake pattern for dependency injection and testing.

## Core Gateways

Located in `packages/erk-shared/src/erk_shared/`:

### Git (`git/`)

Git operations abstraction. See `git/abc.py` for full method list.

**Fake Features**: In-memory worktree state, branch tracking, configurable return values.

### GitHub (`github/`)

GitHub PR and repository operations.

**Fake Features**: In-memory PR state, configurable PR responses, label tracking, mutation tracking via `added_labels` property.

### GitHub Issues (`github/issues/`)

GitHub issue operations.

**Fake Features**: In-memory issue storage, comment tracking, state management.

## Domain Gateways

Located in `packages/erk-shared/src/erk_shared/gateway/`:

### Browser (`browser/`)

System browser launch abstraction.

**Fake Features**: Success mode toggle, launch call tracking via `launched_urls` property.

### Clipboard (`clipboard/`)

System clipboard abstraction.

**Fake Features**: Success mode toggle, copy call tracking via `copied_texts` property.

### Time (`time/`)

Time operations abstraction for testable delays.

**Fake Features**: Fixed time injection, sleep call tracking via `sleep_calls` property, instant returns (no actual sleeping).

### Graphite (`graphite/`)

Graphite stack management operations.

**Fake Features**: Extensive state injection (branch relationships, PR info), parent/child tracking, submit call tracking.

### Erk Worktree (`erk_wt/`)

Erk worktree kit operations.

**Fake Features**: In-memory worktree state, deletion tracking.

### Session Store (`extraction/claude_code_session_store/`)

Claude Code session data operations.

**Fake Features**: Configurable session data, project directory injection.

### Parallel Task Runner (`parallel/`)

Parallel execution abstraction.

**Note**: No fake implementation - uses real ThreadPoolExecutor. Mock at task level instead.

## Implementation Layers

Each gateway typically has these implementations:

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

## Adding New Gateways

When adding a new gateway:

1. Create `abc.py` with interface definition
2. Create `real.py` with production implementation
3. Create `fake.py` with in-memory test implementation
4. Create `dry_run.py` if operations are destructive (optional)
5. Add to `__init__.py` with re-exports
6. Update `ErkContext` to include new gateway

**Related**: [Erk Architecture Patterns](erk-architecture.md#gateway-directory-structure)
