---
title: Erk Test Reference
read_when:
  - "writing tests for erk"
  - "using erk fakes"
  - "running erk test commands"
tripwires:
  - action: "modifying business logic in src/ without adding a test"
    warning: "Bug fixes require regression tests (fails before, passes after). Features require behavior tests."
  - action: "implementing interactive prompts with ctx.console.confirm()"
    warning: "Ensure FakeConsole in test fixture is configured with `confirm_responses` parameter. See tests/commands/submit/test_existing_branch_detection.py for examples."
  - action: "accessing FakeGit properties in tests"
    warning: "Access properties via subgateway (e.g., `git.commit_ops.staged_files`), not top-level."
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

- `Path("/tmp/foo").resolve()` → `/private/tmp/foo`
- `Path("/var/folders/...").resolve()` → `/private/var/folders/...`

**Impact on tests:** If FakeGit is configured with unresolved paths but the code under test calls `.resolve()`, lookups fail.

**FakeGit handles this automatically** - all path lookups resolve both the input and configured paths before comparison. You generally don't need to worry about this.

**If you see path mismatch errors:** Ensure FakeGit's path resolution methods are being used (they handle symlinks), not direct dict lookups.

#### FakeGit Property Access

After Phase 8 refactoring, FakeGit uses subgateways for all operations. Access mutation tracking properties via subgateway, not top-level:

```python
# CORRECT - Access via subgateway
git.commit_ops.staged_files
git.branch_ops.deleted_branches
git.worktree_ops.added_worktrees

# INCORRECT - No top-level properties
git.staged_files  # AttributeError
git.deleted_branches  # AttributeError
```

#### FakeWorktree Error Injection Pattern

When testing discriminated union error paths in gateway methods, use constructor-injected error parameters. The FakeGitWorktree gateway demonstrates the canonical pattern:

**Naming convention**: `{method_name}_error` (e.g., `add_worktree_error`, `remove_worktree_error`)

**Constructor pattern**:

```python
from erk_shared.gateway.git.worktree import FakeGitWorktree
from erk_shared.gateway.git.worktree.types import WorktreeAddError, WorktreeRemoveError

fake_worktree = FakeGitWorktree(
    add_worktree_error=WorktreeAddError(
        path=Path("/path/to/worktree"),
        branch="feature",
        message="Worktree already exists",
    ),
    remove_worktree_error=WorktreeRemoveError(
        path=Path("/path/to/worktree"),
        message="Worktree is locked",
    ),
)
```

**Implementation pattern** (inside FakeGitWorktree):

```python
def add_worktree(self, *, repo_root: Path, path: Path, branch: str) -> WorktreeAdded | WorktreeAddError:
    # Check injected error FIRST (before any success logic)
    if self._add_worktree_error is not None:
        return self._add_worktree_error

    # Success path
    return WorktreeAdded(path=path, branch=branch)
```

**Key principle**: Error injection is checked FIRST in the method body, before any success logic executes.

**Test pattern for success path**:

```python
def test_add_worktree_success() -> None:
    """Test successful worktree addition."""
    fake_worktree = FakeGitWorktree()  # No error injected
    result = fake_worktree.add_worktree(
        repo_root=Path("/repo"),
        path=Path("/repo/.worktrees/feature"),
        branch="feature",
    )
    assert isinstance(result, WorktreeAdded)
    assert result.path == Path("/repo/.worktrees/feature")
    assert result.branch == "feature"
```

**Test pattern for error path**:

```python
def test_add_worktree_error() -> None:
    """Test worktree addition failure."""
    error = WorktreeAddError(
        path=Path("/repo/.worktrees/feature"),
        branch="feature",
        message="Worktree already exists",
    )
    fake_worktree = FakeGitWorktree(add_worktree_error=error)

    result = fake_worktree.add_worktree(
        repo_root=Path("/repo"),
        path=Path("/repo/.worktrees/feature"),
        branch="feature",
    )

    assert isinstance(result, WorktreeAddError)
    assert result.message == "Worktree already exists"
    assert result.error_type == "worktree-add-failed"
```

**Reference test patterns**: Tests in `tests/unit/gateway/git/worktree/` demonstrate success and error path testing for both `add_worktree` and `remove_worktree` operations.

**Cross-reference**: See [gateway-fake-testing-exemplar.md](../architecture/gateway-fake-testing-exemplar.md) for comprehensive fake testing patterns.

### FakeConfigStore

```python
from tests.fakes.config import FakeConfigStore

config_store = FakeConfigStore(
    exists: bool = True,
    erks_root: Path | None = None,
    use_graphite: bool = False,
    shell_setup_complete: bool = False,
    show_pr_checks: bool = False,
)
```

### FakeGitHub

```python
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo

github = FakeGitHub(
    prs: dict[str, PullRequestInfo] = {},  # Branch -> PR info
    pr_details: dict[int, PRDetails] = {},  # PR number -> full details
)
```

**Important: Dual-mapping for branch lookups**

`get_pr_for_branch()` requires BOTH `prs` AND `pr_details` to be configured:

```python
# For get_pr_for_branch() to work, configure both mappings:
pr_info = PullRequestInfo(
    number=123, state="OPEN", url="https://github.com/...",
    is_draft=False, title="My PR", checks_passing=True,
    owner="owner", repo="repo",
)
pr_details = PRDetails(
    number=123, state="OPEN", branch="feature-branch",
    base_branch="main", title="My PR", body="Description",
    url="https://github.com/...", is_draft=False,
    owner="owner", repo="repo",
)

github = FakeGitHub(
    prs={"feature-branch": pr_info},      # Step 1: branch -> PR number
    pr_details={123: pr_details},          # Step 2: PR number -> details
)
```

If only `prs` is configured, `get_pr_for_branch()` returns `PRNotFound` because the second lookup fails.

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

## Fake Error Simulation

Fakes support error simulation via constructor parameters. This pattern is used extensively in gateway testing for discriminated union error handling.

**Pattern**: Error parameters accept the error discriminant type:

```python
from tests.fakes.git_branch_ops import FakeGitBranchOps
from erk.gateway.git_branch_ops.types import CreateBranchResult

fake = FakeGitBranchOps(
    create_branch_error=CreateBranchResult(
        type="branch_already_exists",
        branch_name="feature",
    )
)

result = fake.create_branch(name="feature", start_point="main")
assert result.type == "branch_already_exists"
```

**Benefits:**

- Fast: No subprocess overhead
- Deterministic: Error behavior controlled by test
- Type-safe: Constructor param matches method return type
- Realistic: Uses same discriminant types as real implementation

**Common error simulation patterns:**

```python
# Simulate branch already exists
FakeGitBranchOps(
    create_branch_error=CreateBranchResult(
        type="branch_already_exists",
        branch_name="existing-branch",
    )
)

# Simulate worktree add failure
FakeWorktreeOps(
    add_worktree_error=AddWorktreeResult(
        type="worktree_path_occupied",
        path=Path("/path/to/worktree"),
    )
)

# Simulate generic error
FakeGitBranchOps(
    create_branch_error=CreateBranchResult(
        type="error",
        message="git command failed",
    )
)
```

**Error boundary testing**: Fakes do NOT use try/except (see [Gateway Error Boundaries](../architecture/gateway-error-boundaries.md)). They return error discriminants based on constructor params, making error paths easy to test without mocking exceptions.

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
├── Create/write files directly? → erk_isolated_fs_env()
├── Call .exists()/.is_dir() on paths? → erk_isolated_fs_env()
├── Only use injected fakes? → erk_inmem_env()
└── Need real git commands? → cli_test_repo()
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

### Script Writer Fixture Selection

Different test fixtures use different script writer implementations:

| Fixture               | Script Writer       | How to Read Scripts                    |
| --------------------- | ------------------- | -------------------------------------- |
| `erk_inmem_env`       | `InMemScriptWriter` | `script_writer.get_script_content(id)` |
| `erk_isolated_fs_env` | `RealScriptWriter`  | `script_path.read_text()`              |

**Pattern for `erk_inmem_env` tests:**

```python
with erk_inmem_env() as env:
    script_writer = InMemScriptWriter()
    # ... invoke command that writes script ...
    script = script_writer.get_script_content(script_id)
    assert "expected content" in script
```

**Pattern for `erk_isolated_fs_env` tests:**

```python
with erk_isolated_fs_env(runner) as env:
    # ... invoke command that writes script to filesystem ...
    script = script_path.read_text()
    assert "expected content" in script
```

Choose the fixture based on what you're testing - use `erk_inmem_env` for pure logic with fakes, use `erk_isolated_fs_env` when scripts are written to the real filesystem.

## Branch Divergence Testing

Testing code that validates local vs remote branch divergence requires specific FakeGit setup.

### Setting Up Diverged Branches

```python
from tests.fakes.gitops import FakeGit

# Set up diverged local and remote branches
fake_git = FakeGit()
fake_git.branch_heads = {
    "feature-branch": "abc1234",       # Local has different commit
    "origin/feature-branch": "def5678", # Remote has different commit
}
fake_git.local_branches = {"feature-branch", "main"}
```

### Testing Divergence Detection

```python
def test_divergence_raises_error() -> None:
    fake_git = FakeGit()
    fake_git.branch_heads = {
        "parent": "local-sha",
        "origin/parent": "remote-sha",  # Different from local
    }
    fake_git.local_branches = {"parent", "main"}

    branch_manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=FakeGitBranchOps(),
        graphite=FakeGraphite(),
        graphite_branch_ops=FakeGraphiteBranchOps(),
        github=FakeGitHub(),
    )

    with pytest.raises(RuntimeError, match="has diverged"):
        branch_manager.create_branch(repo_root, "child", "origin/parent")
```

### Testing Sync Scenarios

```python
def test_synced_branches_succeed() -> None:
    fake_git = FakeGit()
    fake_git.branch_heads = {
        "parent": "same-sha",
        "origin/parent": "same-sha",  # Same as local
    }
    # ... should succeed without error
```

## FakeGraphite Sub-Gateway Linking

When testing code that uses `GraphiteBranchManager`, you need to link FakeGraphite with its FakeGraphiteBranchOps sub-gateway.

### The create_linked_branch_ops() Pattern

```python
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.branch_ops.fake import FakeGraphiteBranchOps

# Create linked fake pair
fake_graphite = FakeGraphite()
fake_graphite_branch_ops = FakeGraphiteBranchOps()

# Use in GraphiteBranchManager
branch_manager = GraphiteBranchManager(
    git=fake_git,
    git_branch_ops=fake_git_branch_ops,
    graphite=fake_graphite,
    graphite_branch_ops=fake_graphite_branch_ops,
    github=fake_github,
)
```

### Asserting on Sub-Gateway Mutations

```python
def test_branch_tracked_via_graphite() -> None:
    fake_graphite_branch_ops = FakeGraphiteBranchOps()
    # ... set up branch_manager with fake_graphite_branch_ops ...

    branch_manager.create_branch(repo_root, "feature", "main")

    # Assert on sub-gateway mutations
    assert ("feature", "main") in fake_graphite_branch_ops.tracked_branches
```

## BranchManager Test Placement

Tests for BranchManager implementations live in:

```
tests/unit/branch_manager/
├── test_git_branch_manager.py      # GitBranchManager tests
├── test_graphite_branch_manager.py # GraphiteBranchManager tests
└── test_fake_branch_manager.py     # FakeBranchManager tests
```

Integration tests for real sub-gateways:

```
tests/integration/
├── test_real_git_branch_ops.py
└── test_real_graphite_branch_ops.py
```

## FakeConsole for Interactive Prompts

FakeConsole enables testing code that uses `ctx.console.confirm()` for user prompts.

### Constructor Parameters

```python
FakeConsole(
    is_interactive=True,        # Whether stdin is TTY
    is_stdout_tty=None,         # Defaults to is_interactive
    is_stderr_tty=None,         # Defaults to is_interactive
    confirm_responses=[...],    # List of boolean responses
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

## Test Naming for Return Type Refactoring

When refactoring gateway methods from exception-based to discriminated unions, update test names to reflect the new pattern.

### Pattern: Exception → Union

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

### Example: merge_pr Migration

From PR #6294:

**Before (Exception/Boolean):**

```python
def test_merge_pr_success_returns_true() -> None:
    """Test merge_pr returns True on success."""
    result = github.merge_pr(repo_root, 123)
    assert result is True

def test_merge_pr_failure_returns_error_string() -> None:
    """Test merge_pr returns error string on failure."""
    result = github.merge_pr(repo_root, 999)  # triggers error
    assert isinstance(result, str)
    assert "failed" in result.lower()
```

**After (Discriminated Union):**

```python
def test_merge_pr_returns_merge_result() -> None:
    """Test merge_pr returns MergeResult on success."""
    result = github.merge_pr(repo_root, 123)
    assert isinstance(result, MergeResult)
    assert result.pr_number == 123

def test_merge_pr_returns_merge_error() -> None:
    """Test merge_pr returns MergeError on failure."""
    result = github.merge_pr(repo_root, 999)
    assert isinstance(result, MergeError)
    assert result.pr_number == 999
    assert "failed" in result.message.lower()
```

**Key Changes:**

- Test names describe return types (not booleans/exceptions)
- Assertions check `isinstance(result, Type)` (not `is True` or exception catching)
- Docstrings describe what's returned (not what's raised)

## Related

- **Testing philosophy**: Load `fake-driven-testing` skill
- **Rebase conflicts**: [rebase-conflicts.md](rebase-conflicts.md)
- **Gateway implementation**: [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md)
