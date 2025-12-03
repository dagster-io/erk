---
title: Erk Test Reference
read_when:
  - "writing tests for erk"
  - "using erk fakes"
  - "running erk test commands"
---

# Erk Test Reference

**For testing philosophy and patterns**: Load the `fake-driven-testing` skill first. This document covers erk-specific implementations only.

## Running Tests

```bash
# Fast unit tests (recommended for development)
make test

# Integration tests only (slower, real I/O)
make test-integration

# All tests (unit + integration)
make test-all

# Full CI validation
make all-ci
```

| Target                  | What It Runs                               | Speed   |
| ----------------------- | ------------------------------------------ | ------- |
| `make test`             | Unit tests (tests/unit/, commands/, core/) | ⚡ Fast |
| `make test-integration` | Integration tests (tests/integration/)     | 🐌 Slow |
| `make test-all`         | Both unit + integration                    | 🐌 Slow |

## Test Directory Structure

```
tests/
├── unit/              # Unit tests (fakes, in-memory)
├── integration/       # Integration tests (real I/O)
├── commands/          # CLI command tests (unit tests with fakes)
├── core/              # Core logic tests (unit tests with fakes)
├── fakes/             # Fake implementations
└── test_utils/        # Test helpers (env_helpers, builders)
```

## Erk Fakes Reference

### FakeGit

```python
from tests.fakes.gitops import FakeGit

git = FakeGit(
    worktrees: dict[Path, list[WorktreeInfo]] = {},
    current_branches: dict[Path, str] = {},
    default_branches: dict[Path, str] = {},
    git_common_dirs: dict[Path, Path] = {},
)

# Mutation tracking (read-only)
git.deleted_branches: list[str]
git.added_worktrees: list[tuple[Path, str | None]]
git.removed_worktrees: list[Path]
git.checked_out_branches: list[tuple[Path, str]]
```

### FakeConfigStore

```python
from tests.fakes.config import FakeConfigStore

config_store = FakeConfigStore(
    exists: bool = True,
    erks_root: Path | None = None,
    use_graphite: bool = False,
    shell_setup_complete: bool = False,
    show_pr_info: bool = True,
    show_pr_checks: bool = False,
)
```

### FakeGitHub

```python
from tests.fakes.github import FakeGitHub
from erk_shared.github.types import PullRequestInfo

github = FakeGitHub(
    prs: dict[str, PullRequestInfo] = {},
)
```

### FakeGraphite

```python
from tests.fakes.graphite import FakeGraphite

graphite = FakeGraphite(
    stacks: dict[Path, list[str]] = {},
    current_branch_in_stack: dict[Path, bool] = {},
)
```

### FakeShell

```python
from tests.fakes.shell import FakeShell

shell = FakeShell(
    detected_shell: tuple[str, Path] | None = None,
    installed_tools: dict[str, str] = {},
)
```

## Test Context Helpers

### create_test_context()

```python
from tests.fakes.context import create_test_context

# Minimal context (all fakes with defaults)
ctx = create_test_context()

# Custom fakes
ctx = create_test_context(
    git=FakeGit(worktrees={...}),
    config_store=FakeConfigStore(erks_root=Path("/tmp/ws")),
    dry_run=True,
)
```

### ErkContext.for_test()

```python
from erk.core.context import ErkContext

test_ctx = ErkContext.for_test(
    git=git,
    global_config=global_config,
    cwd=env.cwd,
)
```

## Test Environment Helpers

### erk_isolated_fs_env() (Recommended)

```python
from tests.test_utils.env_helpers import erk_isolated_fs_env

def test_command() -> None:
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # env provides: cwd, git_dir, root_worktree, erks_root
        git = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = ErkContext.for_test(git=git, cwd=env.cwd)

        result = runner.invoke(cli, ["command"], obj=test_ctx)
        assert result.exit_code == 0
```

### erk_inmem_env() (For sentinel paths)

Use when you don't need real filesystem isolation:

```python
from tests.test_utils.env_helpers import erk_inmem_env

def test_logic() -> None:
    with erk_inmem_env() as env:
        # env provides sentinel paths for pure logic tests
        git = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # ...
```

### cli_test_repo() (For real git)

Only use when testing actual git operations:

```python
from tests.test_utils.cli_helpers import cli_test_repo

def test_git_integration(tmp_path: Path) -> None:
    with cli_test_repo(tmp_path) as test_env:
        # test_env.repo: Real git repository
        # test_env.erks_root: Configured erks directory
        # ...
```

## CLI Testing Pattern

```python
from click.testing import CliRunner
from erk.cli.cli import cli

def test_create_command() -> None:
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )
        test_ctx = ErkContext.for_test(git=git, cwd=env.cwd)

        result = runner.invoke(cli, ["create", "feature"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Created" in result.output
        assert len(git.added_worktrees) == 1
```

## 🔴 CRITICAL: Never Hardcode Paths

```python
# ❌ FORBIDDEN - breaks in CI, risks global config mutation
cwd=Path("/test/default/cwd")

# ✅ CORRECT - use environment helpers
with erk_isolated_fs_env(runner) as env:
    cwd=env.cwd
```

## Related

- **Testing philosophy**: Load `fake-driven-testing` skill
- **Rebase conflicts**: [rebase-conflicts.md](rebase-conflicts.md)
