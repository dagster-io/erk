---
title: Erk Test Reference
last_audited: "2026-02-13 00:00 PT"
audit_result: clean
read_when:
  - "writing tests for erk"
  - "using erk fakes"
  - "running erk test commands"
tripwires:
  - action: "modifying business logic in src/ without adding a test"
    warning: "Bug fixes require regression tests (fails before, passes after). Features require behavior tests."
  - action: "implementing interactive prompts with ctx.console.confirm()"
    warning: "Ensure FakeConsole in test fixture is configured with `confirm_responses` parameter. Array length must match prompt count exactly — too few causes IndexError, too many indicates a removed prompt. See tests/commands/submit/test_existing_branch_detection.py for examples."
  - action: "accessing FakeGit properties in tests"
    warning: "FakeGit has top-level properties (e.g., `git.staged_files`, `git.deleted_branches`, `git.added_worktrees`). Worktree operations delegate to an internal FakeWorktree sub-gateway."
  - action: "asserting on fake-specific properties in tests using `build_workspace_test_context` with `use_graphite=True`"
    warning: "Production wrappers (e.g., `GraphiteBranchManager`) do not expose fake tracking properties like `submitted_branches`. Assert on observable behavior (CLI output, return values) instead of accessing fake internals through the wrapper."
---

# Erk Test Reference

**For testing philosophy and patterns**: Load the `fake-driven-testing` skill first. This document covers erk-specific implementations only.

## Test Requirements for Code Changes

All business logic changes in `src/` must include corresponding tests:

- **Bug fixes**: Add a regression test that fails before the fix and passes after
- **Features**: Add tests covering the new behavior

If existing tests pass after your change, either:

1. The tests weren't covering the changed code path, or
2. You need to add a new test for the specific scenario

**Anti-pattern:** Fixing a bug without a regression test. This allows the bug to be reintroduced later.

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

| Target                  | What It Runs                               | Speed |
| ----------------------- | ------------------------------------------ | ----- |
| `make test`             | Unit tests (tests/unit/, commands/, core/) | Fast  |
| `make test-integration` | Integration tests (tests/integration/)     | Slow  |
| `make test-all`         | Both unit + integration                    | Slow  |

## Progressive Test Verification

When implementing changes, verify in expanding scope:

1. **Specific test file** -- Run only the test file for the function you changed (e.g., `test_graphite_first_flow.py`)
2. **Module test suite** -- Run the broader test directory (e.g., all `submit_pipeline/` tests)
3. **Full CI** -- Run `make fast-ci` for complete validation

This catches issues at the narrowest scope first, keeping the feedback loop fast. Don't jump straight to `make fast-ci` after a small change.

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

See `FakeGit` class in `packages/erk-shared/src/erk_shared/gateway/git/fake.py`.

FakeGit provides top-level properties for test assertions:

```python
# Top-level properties available on FakeGit
git.staged_files        # list[str] - files staged via add/stage
git.deleted_branches    # list[str] - branches deleted via delete_branch()
git.added_worktrees     # list[tuple[Path, str | None]] - worktrees added
git.removed_worktrees   # list[Path] - worktrees removed
git.created_branches    # list[tuple[Path, str, str, bool]] - branches created
git.pushed_branches     # list[PushedBranch] - branches pushed
git.commits             # list[CommitRecord] - commits made
```

Worktree operations are internally delegated to a `FakeWorktree` sub-gateway, but the top-level properties on `FakeGit` provide convenient access.

#### FakeGit Path Resolution

FakeGit methods that accept paths perform intelligent lookups:

**`get_git_common_dir(cwd)`** - Walks up parent directories to find a match, handles symlink resolution (macOS `/var` vs `/private/var`).

**`get_repository_root(cwd)`** - Resolution order:

1. Explicit `repository_roots` mapping
2. Inferred from `worktrees` (finds deepest worktree containing cwd)
3. Derived from `git_common_dirs` (parent of .git directory)
4. Falls back to cwd

**`list_worktrees(repo_root)`** - Can be called from any worktree path or main repo, not just the dict key.

**Common Gotcha:** When testing subdirectories of worktrees, you often don't need to configure `repository_roots` explicitly - FakeGit infers it from the `worktrees` configuration.

```python
# Testing from a subdirectory of a worktree
git_ops = FakeGit(
    worktrees={
        main_repo: [
            WorktreeInfo(path=main_repo, branch="main", is_root=True),
            WorktreeInfo(path=worktree_path, branch="feature", is_root=False),
        ]
    },
    git_common_dirs={subdirectory: main_repo / ".git"},
    # No need for repository_roots - inferred from worktrees
)
```

#### macOS Symlink Resolution

On macOS, `/tmp` and `/var` are symlinks to `/private/tmp` and `/private/var`. When paths are resolved:

- `Path("/tmp/foo").resolve()` -> `/private/tmp/foo`
- `Path("/var/folders/...").resolve()` -> `/private/var/folders/...`

**Impact on tests:** If FakeGit is configured with unresolved paths but the code under test calls `.resolve()`, lookups fail.

**FakeGit handles this automatically** - all path lookups resolve both the input and configured paths before comparison. You generally don't need to worry about this.

**If you see path mismatch errors:** Ensure FakeGit's path resolution methods are being used (they handle symlinks), not direct dict lookups.

#### FakeWorktree Error Injection

FakeWorktree (in `packages/erk-shared/src/erk_shared/gateway/git/worktree/fake.py`) uses string-based error injection via constructor parameters. Errors raise `RuntimeError`:

```python
from erk_shared.gateway.git.worktree.fake import FakeWorktree

# Inject error for add_worktree
fake_worktree = FakeWorktree(
    add_worktree_error="Worktree already exists",
    remove_worktree_error="Worktree is locked",
)
```

When `add_worktree_error` or `remove_worktree_error` is set, the corresponding method raises `RuntimeError` with that message. Error injection is checked FIRST in the method body, before any success logic executes.

You can also inject these errors via the top-level `FakeGit` constructor:

```python
git = FakeGit(
    add_worktree_error="Worktree already exists",
    remove_worktree_error="Worktree is locked",
)
```

### FakeGitHub

See `FakeGitHub` class in `packages/erk-shared/src/erk_shared/gateway/github/fake.py`.

**Important: Dual-mapping for branch lookups** - `get_pr_for_branch()` requires BOTH `prs` AND `pr_details` to be configured. If only `prs` is configured, the method returns `PRNotFound` because the second lookup fails.

### FakeGraphite

See `FakeGraphite` class in `packages/erk-shared/src/erk_shared/gateway/graphite/fake.py`.

### FakeShell

See `FakeShell` class in `packages/erk-shared/src/erk_shared/gateway/shell/fake.py`.

### FakeGitBranchOps

See `FakeGitBranchOps` class in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/fake.py`.

This fake supports error injection via the `create_branch_error` constructor parameter, which accepts a `BranchAlreadyExists` instance:

```python
from erk_shared.gateway.git.branch_ops.fake import FakeGitBranchOps
from erk_shared.gateway.git.branch_ops.types import BranchAlreadyExists

fake = FakeGitBranchOps(
    branch_heads={"feature": "abc123", "origin/feature": "abc123"},
)

# With error injection
fake_with_error = FakeGitBranchOps(
    branch_heads={"feature": "abc123"},
    # create_branch will return BranchAlreadyExists instead of BranchCreated
)
```

## Fixture Selection Guide

### When to Use Each Fixture

| Fixture               | Use When                           | Key Characteristic             |
| --------------------- | ---------------------------------- | ------------------------------ |
| `erk_isolated_fs_env` | Command does real filesystem ops   | Creates real temp directories  |
| `erk_inmem_env`       | Testing pure logic with fakes only | Uses sentinel paths (not real) |
| `cli_test_repo`       | Testing real git operations        | Creates actual git repository  |

### Common Mistake: Sentinel Path Errors

If you see `"Called .exists() on sentinel path"`:

- You're using `erk_inmem_env()` but code is doing real filesystem checks
- **Fix**: Switch to `erk_isolated_fs_env(runner)`

### Decision Tree

```
Does the code under test:
├── Create/write files directly? -> erk_isolated_fs_env()
├── Call .exists()/.is_dir() on paths? -> erk_isolated_fs_env()
├── Only use injected fakes? -> erk_inmem_env()
└── Need real git commands? -> cli_test_repo()
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
    dry_run=True,
)
```

This is a convenience wrapper around `context_for_test()` from `erk.core.context`.

### context_for_test()

```python
from erk.core.context import context_for_test

test_ctx = context_for_test(
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
        test_ctx = context_for_test(git=git, cwd=env.cwd)

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
        test_ctx = context_for_test(git=git, cwd=env.cwd)

        result = runner.invoke(cli, ["create", "feature"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Created" in result.output
        assert len(git.added_worktrees) == 1
```

## CRITICAL: Never Hardcode Paths

```python
# FORBIDDEN - breaks in CI, risks global config mutation
cwd=Path("/test/default/cwd")

# CORRECT - use environment helpers
with erk_isolated_fs_env(runner) as env:
    cwd=env.cwd
```

## Testing Notes

### shlex.quote() Behavior

When testing code that uses `shlex.quote()` for path quoting:

- `shlex.quote()` only adds quotes for paths containing special characters (spaces, `$`, etc.)
- Simple paths like `/tmp/foo` remain unquoted
- Tests should not hardcode quoted paths like `'{path}'`

**Wrong:**

```python
# Assumes quotes are always present
assert f"git worktree remove '{worktree_path}'" in script
```

**Correct:**

```python
# Use shlex.quote() in assertions to match actual behavior
assert f"git worktree remove {shlex.quote(str(worktree_path))}" in script

# Or check for command presence without quote assumptions
assert "git worktree remove" in script
assert str(worktree_path) in script
```

## FakeConsole for Interactive Prompts

FakeConsole enables testing code that uses `ctx.console.confirm()` for user prompts.

Source: `packages/erk-shared/src/erk_shared/gateway/console/fake.py`

### Constructor Parameters

All parameters are required keyword-only arguments:

```python
from erk_shared.gateway.console.fake import FakeConsole

FakeConsole(
    is_interactive=True,        # Whether stdin is TTY
    is_stdout_tty=None,         # Defaults to is_interactive if None
    is_stderr_tty=None,         # Defaults to is_interactive if None
    confirm_responses=[...],    # List of boolean responses (None for no confirms)
)
```

### Testing Pattern

Configure `confirm_responses` with the sequence of True/False values:

```python
from tests.test_utils.env_helpers import erk_isolated_fs_env

def test_with_user_confirmation() -> None:
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        ctx = env.context_for_test(
            confirm_responses=[True, False],  # First prompt: Yes, Second: No
        )

        result = runner.invoke(cli, ["command"], obj=ctx)

        assert result.exit_code == 0
```

### Assertion Helpers

```python
# Check what prompts were shown
assert "Delete file?" in fake_console.confirm_prompts

# Check captured messages
fake_console.assert_contains("Operation complete")
fake_console.assert_not_contains("Error")
```

### Error Behavior

If `confirm()` is called but no responses remain, FakeConsole raises `AssertionError` with the prompt text. This catches missing test setup.

### Example Tests

See `tests/commands/submit/test_existing_branch_detection.py` for comprehensive examples of testing interactive prompts.

## GraphiteBranchManager Testing

`GraphiteBranchManager` is a frozen dataclass in `packages/erk-shared/src/erk_shared/gateway/branch_manager/graphite.py` with fields:

```python
@dataclass(frozen=True)
class GraphiteBranchManager(BranchManager):
    git: Git
    graphite: Graphite
    graphite_branch_ops: GraphiteBranchOps
    github: GitHub
```

### Test Setup Pattern

```python
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.branch_ops.fake import FakeGraphiteBranchOps
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.branch_manager.graphite import GraphiteBranchManager

branch_manager = GraphiteBranchManager(
    git=FakeGit(...),
    graphite=FakeGraphite(...),
    graphite_branch_ops=FakeGraphiteBranchOps(),
    github=FakeGitHub(...),
)
```

### BranchManager Test Placement

Tests for GraphiteBranchManager live in:

```
tests/unit/branch_manager/
└── test_graphite_branch_manager.py
```

Integration tests for real sub-gateways:

```
tests/integration/
├── test_real_git_branch_ops.py
└── test_real_graphite_branch_ops.py
```

## Test Naming for Return Type Refactoring

When refactoring gateway methods from exception-based to discriminated unions, update test names to reflect the new pattern.

### Pattern: Exception -> Union

| Old Test Name (Exception-Based)       | New Test Name (Discriminated Union)      |
| ------------------------------------- | ---------------------------------------- |
| `test_merge_pr_failure_returns_false` | `test_merge_pr_returns_merge_error`      |
| `test_merge_pr_success_returns_true`  | `test_merge_pr_returns_merge_result`     |
| `test_get_issue_raises_not_found`     | `test_get_issue_returns_issue_not_found` |
| `test_get_issue_raises_api_error`     | `test_get_issue_returns_api_error`       |

### Naming Conventions

**Success Case:**

- Old: `test_<method>_success` or `test_<method>_returns_true`
- New: `test_<method>_returns_<success_type>`

**Error Case:**

- Old: `test_<method>_raises_<error>` or `test_<method>_returns_false`
- New: `test_<method>_returns_<error_type>`

### Migration Checklist

When renaming tests for discriminated union migration:

1. [ ] Update test name to use `returns_<type>` pattern
2. [ ] Update test body to check `isinstance(result, Type)`
3. [ ] Update docstring to describe return type (not exception)
4. [ ] Verify fake setup returns type (not raises exception)
5. [ ] Update related parametrized test names

## Test Fixture Maintenance on Signature Changes

When function signatures change (e.g., adding a column to a table, adding a new parameter), **all test fixtures must be updated comprehensively**. Partial updates cause hard-to-debug failures.

### Checklist

1. Find all test files that call the changed function: `grep -r "function_name" tests/`
2. Update every fixture and test data structure to match the new signature
3. Run the full test suite — don't rely on just running the tests you think are affected
4. Check for builder functions or factory helpers that construct test data — these need updates too

### Common Mistake

Updating the implementation and the directly-tested function, but missing test helpers, builders, or parametrized test data that also construct instances of the changed type.

## Dependency Customization Preference

Prefer **parameter injection** over monkeypatch for dependency customization in tests:

- **Parameter injection**: Pass test values as keyword-only parameters to functions. No monkeypatch needed, explicit dependencies, cleaner test code.
- **Monkeypatch**: Fallback when parameter injection isn't feasible (e.g., CLI integration tests that exercise the full Click boundary).

See [Parameter Injection Pattern](parameter-injection-pattern.md) for the complete guide.

## Related

- **Testing philosophy**: Load `fake-driven-testing` skill
- **Rebase conflicts**: [rebase-conflicts.md](rebase-conflicts.md)
- **Gateway implementation**: [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md)
- **Parameter injection**: [Parameter Injection Pattern](parameter-injection-pattern.md)
