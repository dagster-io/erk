---
title: Test Architecture
read_when:
  - "writing tests with fakes"
  - "understanding ops pattern"
  - "running tests"
---

# Test Architecture: Coarse-Grained Dependency Injection

## Running Tests

### Quick Start

```bash
# Fast unit tests (recommended for development iteration)
make test

# Integration tests only (slower, real I/O)
make test-integration

# All tests (unit + integration, comprehensive validation)
make test-all
```

### Test Targets Explained

| Target                      | What It Runs                                                         | Speed       | Use Case                                                          |
| --------------------------- | -------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------- |
| **`make test`**             | Unit tests only<br>(`tests/unit/`, `tests/commands/`, `tests/core/`) | ⚡⚡⚡ Fast | **Default for development**<br>Quick feedback during coding       |
| **`make test-integration`** | Integration tests only<br>(`tests/integration/`)                     | 🐌 Slower   | Verify external tool integration<br>(git, filesystem, subprocess) |
| **`make test-all`**         | Both unit + integration<br>(comprehensive)                           | 🐌 Slowest  | Pre-commit validation<br>CI runs this target                      |

### Test Categories

#### Unit Tests (~90-95% of test suite)

**Characteristics:**

- ⚡ Very fast (in-memory, uses fakes)
- Uses `FakeGit`, `FakeGraphite`, `FakeGitHub`, `FakeShell`
- Uses `CliRunner` for CLI tests (NOT subprocess)
- Uses `erk_inmem_env()` (sentinel paths) or `erk_isolated_fs_env()` (isolated filesystem)
- No external system calls
- No `time.sleep()` calls (use mocking or dependency injection)

**Locations:**

- `tests/unit/` - Unit tests of core components
- `tests/commands/` - CLI command tests using fakes
- `tests/core/` - Business logic tests using fakes

**Run with:** `make test`

#### Integration Tests (~5-10% of test suite)

**Characteristics:**

- 🐌 Slower (real filesystem I/O, subprocess calls)
- Uses `RealGit`, `RealGraphite`, etc.
- Uses `tmp_path` pytest fixture for real directories
- Calls actual git commands via `subprocess.run()`
- Tests that abstraction layers correctly wrap external tools
- Tests that invoke subprocess calls to external tools

**Location:** `tests/integration/`

**Run with:** `make test-integration`

### 🔴 Test Categorization Rules (CRITICAL)

**A test MUST be categorized as an integration test if:**

1. **It invokes a subprocess** - Any test that calls `subprocess.run()`, `subprocess.Popen()`, or similar
2. **It uses `time.sleep()`** - Tests that rely on actual timing delays (unless testing time-critical behavior)
3. **It performs extensive real filesystem I/O** - Tests that interact with external filesystem locations, create many files, or depend on actual filesystem behavior (limited file I/O with `isolated_filesystem()` or `tmp_path` in unit tests is acceptable)
4. **It tests subprocess boundaries** - Tests validating that abstraction layers correctly wrap external tools

**Examples:**

```python
# ❌ WRONG - Unit test with subprocess call
def test_git_status() -> None:
    result = subprocess.run(["git", "status"], capture_output=True)
    # This MUST go in tests/integration/

# ❌ WRONG - Unit test with time.sleep()
def test_retry_with_backoff() -> None:
    time.sleep(0.5)  # Actual delay
    # This MUST go in tests/integration/ OR use mocking/DI

# ✅ CORRECT - Integration test with subprocess
def test_real_git_status(tmp_path: Path) -> None:
    # Located in tests/integration/
    result = subprocess.run(["git", "status"], cwd=tmp_path, capture_output=True)
    assert result.returncode == 0

# ✅ CORRECT - Unit test with mocked sleep
def test_retry_with_backoff(monkeypatch) -> None:
    # Located in tests/unit/ or tests/commands/
    mock_sleep = Mock()
    monkeypatch.setattr("time.sleep", mock_sleep)
    # Test logic without actual delay
```

**Why this matters:**

- **CI performance**: Unit tests must remain fast for quick feedback
- **Test reliability**: Subprocess calls can fail due to environment differences
- **Parallel execution**: Tests with subprocesses may have race conditions
- **Resource usage**: Subprocess tests consume more system resources

**If you're unsure:** Default to integration test. It's safer to categorize a test as integration than to slow down the unit test suite.

### CI Configuration

**CI runs comprehensive validation:**

```bash
make all-ci  # Runs: lint, format-check, prettier-check, md-check, pyright, test-all, check
```

This ensures both unit and integration tests pass before merging.

### Directory-Based Filtering

Tests are organized by type using directory structure (no pytest markers needed):

```
tests/
├── unit/              # Unit tests (fakes, in-memory)
├── integration/       # Integration tests (real I/O)
├── commands/          # CLI command tests (unit tests with fakes)
└── core/              # Core logic tests (unit tests with fakes)
```

**Rationale:** Directory-based filtering is simpler and doesn't require modifying test files with markers. The test organization already reflects the unit/integration split.

---

## 🔴 CRITICAL: NEVER Use Hardcoded Paths in Tests

**ABSOLUTELY FORBIDDEN** patterns in test code:

```python
# ❌ WRONG - EXTREMELY DANGEROUS
cwd=Path("/test/default/cwd")
cwd=Path("/some/hardcoded/path")
```

**Why this is catastrophic:**

1. **Global Config Mutation Risk**: If any code tries to write `.erk` config relative to a hardcoded path, it could pollute the REAL filesystem or global config
2. **False Test Isolation**: Tests appear isolated but may share state through hardcoded paths
3. **Unpredictable Failures**: Tests fail in CI/different environments where paths don't exist
4. **Security Risk**: Creating files at hardcoded system paths can be exploited

**ALWAYS use proper context from test fixtures:**

```python
# ✅ CORRECT - Use simulated environment
with erk_isolated_fs_env(runner) as env:
    ctx = ErkContext(..., cwd=env.cwd)

# ✅ CORRECT - Use tmp_path fixture
def test_something(tmp_path: Path) -> None:
    ctx = ErkContext(..., cwd=tmp_path)

# ✅ CORRECT - Use env from simulated helper
ctx = _create_test_context(env, ...)  # env.cwd used internally
```

**If you see `Path("/` in test code, STOP IMMEDIATELY and use proper fixtures.**

---

## Quick Reference

| Testing Scenario              | Use This                                            |
| ----------------------------- | --------------------------------------------------- |
| Unit test CLI command         | FakeGit + FakeConfigStore + context injection       |
| Integration test git behavior | RealGit + tmp_path fixture                          |
| Test dry-run behavior         | create_context(dry_run=True) + assertions on output |
| Test shell detection          | FakeShell with detected_shell parameter             |
| Test tool availability        | FakeShell with installed_tools parameter            |

## Test Organization Principles

### Plain Functions Over Test Classes

**Default pattern: Use plain `def test_*()` functions.** Test classes should only be used when testing a class or dataclass itself.

#### When to Use Test Classes

✅ **ONLY when testing a class or dataclass:**

```python
# ✅ CORRECT: Testing a dataclass
@dataclass(frozen=True)
class DeletableWorktree:
    path: Path
    branch: str

class TestDeletableWorktree:
    def test_equality(self) -> None:
        wt1 = DeletableWorktree(Path("/foo"), "branch")
        wt2 = DeletableWorktree(Path("/foo"), "branch")
        assert wt1 == wt2
```

#### When NOT to Use Test Classes

❌ **WRONG: Using test classes to group related tests:**

```python
# ❌ WRONG - Don't use classes for grouping
class TestWorktreeUtils:
    def test_find_worktree(self) -> None: ...
    def test_is_root_worktree(self) -> None: ...
    def test_get_branch(self) -> None: ...
```

✅ **CORRECT: Use plain functions in single file OR separate module files:**

**Option 1: Single file** (when tests are related and file is manageable)

```python
# tests/core/utils/test_worktree_utils.py

def test_find_worktree() -> None: ...
def test_is_root_worktree() -> None: ...
def test_get_branch() -> None: ...
```

**Option 2: Separate module files** (when splitting improves organization)

```
tests/core/utils/worktree/
├── __init__.py
├── test_find_worktree.py
├── test_is_root_worktree.py
└── test_get_branch.py
```

#### When to Split vs Single File

**Keep as single file when:**

- Testing a single function/utility with multiple test cases
- Splitting would create 4+ files with only 1-2 tests each
- Tests are closely related and benefit from co-location

**Split into subdirectory when:**

- File has 5+ functions being tested AND
- Each new file would have 3+ tests AND
- Splitting improves discoverability

**Example: File with 7 functions, 3-7 tests each:**

- Total: ~30 tests, 450 lines
- Split into `function_name/` subdirectory with 7 files
- Each file has 3-7 related tests
- ✅ Improved navigation and clarity

**Example: File with 3 functions, 3-5 tests each:**

- Total: ~12 tests, 275 lines
- Keep as single file
- Splitting creates only 3 files (below threshold)
- ✅ Avoids excessive file proliferation

## Test Coverage Requirements

### When Tests Are Required

**Every code change falls into one of these categories, each requiring tests:**

| Change Type                          | Test Requirement         | Test Layer          | Example                                                         |
| ------------------------------------ | ------------------------ | ------------------- | --------------------------------------------------------------- |
| **New Feature**                      | MUST have tests          | Fake layer          | Adding `erk merge` command → Test with FakeGit                  |
| **Bug Fix**                          | MUST reproduce then fix  | Fake layer          | Fixing branch detection → Test that reproduces bug, then passes |
| **Business Logic Change**            | MUST have tests          | Fake layer          | Changing worktree naming logic → Test new behavior with fakes   |
| **New Integration Interface Method** | MUST test implementation | Mock stateful calls | Adding `Git.cherry_pick()` → Mock git subprocess, test paths    |

### Default Testing Strategy: Fake Layer

**The default position is that ALL business logic changes require tests written over the fake layer.**

**Why fake layer by default:**

- **Fast execution** - No subprocess calls, no file I/O
- **Deterministic** - Controlled state, predictable results
- **Comprehensive** - Can test all code paths including error cases
- **Maintainable** - Changes to implementation don't break tests

**What counts as business logic:**

- Command behavior and workflow
- Data transformation and formatting
- Decision logic (if/else branches)
- State management and mutations
- User interaction flows

**What doesn't count as business logic:**

- Pure infrastructure (logging setup)
- Configuration constants
- Type definitions
- Documentation

### Testing Integration Class Implementations

**When adding new methods to integration interfaces, you MUST provide test coverage for the real implementation.**

**Pattern for testing integration implementations:**

1. **Test the interface contract with fakes** (for consumers)
2. **Test the real implementation with mocked stateful interactions** (for coverage)

**Example: Adding a new Git method**

```python
# In src/erk/core/git.py
class Git(ABC):
    @abstractmethod
    def stash_changes(self, repo_path: Path, message: str) -> None:
        """Stash uncommitted changes."""
        ...

class RealGit(Git):
    def stash_changes(self, repo_path: Path, message: str) -> None:
        result = subprocess.run(
            ["git", "stash", "push", "-m", message],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise GitError(f"Failed to stash: {result.stderr}")
```

**Test 1: Fake implementation for consumers**

```python
# In tests/fakes/gitops.py
class FakeGit(Git):
    def __init__(self):
        self.stashed_changes: list[tuple[Path, str]] = []

    def stash_changes(self, repo_path: Path, message: str) -> None:
        self.stashed_changes.append((repo_path, message))

# In tests/commands/test_stash.py
def test_stash_command():
    git = FakeGit()
    ctx = create_test_context(git=git)

    result = runner.invoke(cli, ["stash", "WIP"], obj=ctx)

    assert result.exit_code == 0
    assert (".", "WIP") in git.stashed_changes
```

**Test 2: Real implementation with mocked subprocess**

```python
# In tests/integration/test_git.py
from unittest.mock import patch, MagicMock

def test_real_git_stash_success():
    """Test RealGit.stash_changes with successful git stash."""
    ops = RealGit()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        ops.stash_changes(Path("/repo"), "WIP message")

        mock_run.assert_called_once_with(
            ["git", "stash", "push", "-m", "WIP message"],
            cwd=Path("/repo"),
            capture_output=True,
            text=True,
        )

def test_real_git_stash_failure():
    """Test RealGit.stash_changes handles git errors."""
    ops = RealGit()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="error: cannot stash"
        )

        with pytest.raises(GitError, match="Failed to stash"):
            ops.stash_changes(Path("/repo"), "WIP")
```

**Key points for integration implementation testing:**

- Mock at the boundary (subprocess, file I/O, network)
- Test both success and error paths
- Verify correct parameters passed to external systems
- Ensure error messages are meaningful

### Testing Decision Matrix

```
What are you changing?
├─ Adding a feature?
│  └─ Write tests using fake layer
│
├─ Fixing a bug?
│  └─ Write test that reproduces bug with fakes
│     └─ Fix bug so test passes
│
├─ Changing business logic?
│  └─ Write tests using fake layer
│
├─ Adding new integration interface method?
│  ├─ Write fake implementation with mutation tracking
│  ├─ Write tests for consumers using fake
│  └─ Write tests for real implementation with mocks
│
└─ Refactoring without behavior change?
   └─ Existing tests should pass unchanged
```

### Common Testing Patterns

**Feature Addition Pattern:**

```python
def test_new_merge_command():
    """Test new merge command merges worktree branch."""
    git = FakeGit(
        worktrees={repo: [
            WorktreeInfo(path=repo, branch="main"),
            WorktreeInfo(path=wt, branch="feature"),
        ]}
    )
    ctx = create_test_context(git=git)

    result = runner.invoke(cli, ["merge", "feature"], obj=ctx)

    assert result.exit_code == 0
    assert "feature" in git.merged_branches  # Mutation tracking
```

**Bug Fix Pattern:**

```python
def test_branch_detection_with_detached_head():
    """Regression test for bug #123: crash on detached HEAD."""
    # Setup state that reproduces the bug
    git = FakeGit(
        current_branches={repo: None}  # Detached HEAD
    )
    ctx = create_test_context(git=git)

    # This used to crash, now should handle gracefully
    result = runner.invoke(cli, ["current"], obj=ctx)

    assert result.exit_code == 0
    assert "Not on any branch" in result.output
```

**Business Logic Change Pattern:**

```python
def test_new_worktree_naming_convention():
    """Test updated worktree naming includes timestamp."""
    git = FakeGit()
    ctx = create_test_context(git=git)

    with patch("time.time", return_value=1234567890):
        result = runner.invoke(
            cli, ["create", "feature"], obj=ctx
        )

    assert result.exit_code == 0
    # New naming convention includes timestamp
    assert any("feature-1234567890" in str(wt)
              for wt, _ in git.added_worktrees)
```

## Dependency Categories

### 1. Git - Version Control Operations

**Real Implementation**: `RealGit()`
**Dry-Run Wrapper**: `DryRunGit(wrapped)`
**Fake Implementation**: `FakeGit(...)`

**Constructor Parameters**:

```python
FakeGit(
    worktrees: dict[Path, list[WorktreeInfo]] = {},
    current_branches: dict[Path, str] = {},
    default_branches: dict[Path, str] = {},
    git_common_dirs: dict[Path, Path] = {},
)
```

**Mutation Tracking** (read-only properties):

- `git.deleted_branches: list[str]`
- `git.added_worktrees: list[tuple[Path, str | None]]`
- `git.removed_worktrees: list[Path]`
- `git.checked_out_branches: list[tuple[Path, str]]`

**Common Patterns**:

```python
# Pattern 1: Empty git state
git = FakeGit(git_common_dirs={cwd: cwd / ".git"})

# Pattern 2: Pre-configured worktrees
git = FakeGit(
    worktrees={
        repo: [
            WorktreeInfo(path=repo, branch="main"),
            WorktreeInfo(path=wt1, branch="feature"),
        ]
    },
    git_common_dirs={repo: repo / ".git"},
)

# Pattern 3: Track mutations
git = FakeGit(...)
# ... run command ...
assert "feature" in git.deleted_branches
```

### 2. ConfigStore - Configuration Management

**Real Implementation**: `RealConfigStore()`
**Dry-Run Wrapper**: `DryRunConfigStore(wrapped)`
**Fake Implementation**: `FakeConfigStore(...)`

**Constructor Parameters**:

```python
FakeConfigStore(
    exists: bool = True,
    erks_root: Path | None = None,
    use_graphite: bool = False,
    shell_setup_complete: bool = False,
    show_pr_info: bool = True,
    show_pr_checks: bool = False,
)
```

**Common Patterns**:

```python
# Pattern 1: Config exists with values
config_store = FakeConfigStore(
    exists=True,
    erks_root=Path("<temp-dir>/erks"),
    use_graphite=True,
)

# Pattern 2: Config doesn't exist (first-time init)
config_store = FakeConfigStore(exists=False)

# Pattern 3: Test config mutations
config_store = FakeConfigStore(exists=False)
config_store.set(erks_root=Path("<temp-dir>/ws"), use_graphite=True)
assert config_store.get_erks_root() == Path("<temp-dir>/ws")
```

### 3. GitHub - GitHub API Interactions

**Real Implementation**: `RealGitHub()`
**Dry-Run Wrapper**: `DryRunGitHub(wrapped)`
**Fake Implementation**: `FakeGitHub(...)`

**Constructor Parameters**:

```python
FakeGitHub(
    prs: dict[str, PullRequestInfo] = {},
)
```

**Common Patterns**:

```python
# Pattern 1: No PRs
github = FakeGitHub()

# Pattern 2: Pre-configured PRs
from erk_shared.github.types import PullRequestInfo

github = FakeGitHub(
    prs={
        "feature-branch": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            checks_passing=True,
            owner="owner",
            repo="repo",
        ),
    }
)
```

### 4. Graphite - Graphite Tool Operations

**Real Implementation**: `RealGraphite()`
**Dry-Run Wrapper**: `DryRunGraphite(wrapped)`
**Fake Implementation**: `FakeGraphite(...)`

**Constructor Parameters**:

```python
FakeGraphite(
    stacks: dict[Path, list[str]] = {},
    current_branch_in_stack: dict[Path, bool] = {},
)
```

**Common Patterns**:

```python
# Pattern 1: No Graphite stacks
graphite = FakeGraphite()

# Pattern 2: Pre-configured stacks
graphite = FakeGraphite(
    stacks={repo: ["main", "feature-1", "feature-2"]},
    current_branch_in_stack={repo: True},
)
```

### 5. Shell - Shell Detection and Tool Availability

**Real Implementation**: `RealShell()`
**No Dry-Run Wrapper** (read-only operations)
**Fake Implementation**: `FakeShell(...)`

**Constructor Parameters**:

```python
FakeShell(
    detected_shell: tuple[str, Path] | None = None,
    installed_tools: dict[str, str] = {},
)
```

**Common Patterns**:

```python
# Pattern 1: No shell detected
shell = FakeShell()

# Pattern 2: Bash shell detected
shell = FakeShell(
    detected_shell=("bash", Path.home() / ".bashrc")
)

# Pattern 3: Tool installed
shell = FakeShell(
    installed_tools={"gt": "/usr/local/bin/gt"}
)

# Pattern 4: Multiple tools
shell = FakeShell(
    detected_shell=("zsh", Path.home() / ".zshrc"),
    installed_tools={
        "gt": "/usr/local/bin/gt",
        "gh": "/usr/local/bin/gh",
    }
)
```

## Testing Patterns

### Unit Test Pattern

```python
def test_command_behavior() -> None:
    """Test CLI command with fakes."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()

        # Configure fakes with initial state
        git = FakeGit(git_common_dirs={cwd: cwd / ".git"})
        config_store = FakeConfigStore(
            erks_root=cwd / "erks",
            use_graphite=False,
        )

        # Create context with all dependencies
        test_ctx = ErkContext(
            git=git,
            config_store=config_store,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(),
            dry_run=False,
        )

        # Invoke command
        result = runner.invoke(cli, ["command", "args"], obj=test_ctx)

        # Assert on results
        assert result.exit_code == 0
        assert "expected output" in result.output

        # Assert on mutations (if tracking enabled)
        assert len(git.deleted_branches) == 1
```

### Integration Test Pattern

```python
def test_real_git_behavior(tmp_path: Path) -> None:
    """Test with real git operations."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Set up real git repo
    init_git_repo(repo, "main")
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature", str(wt1)],
        cwd=repo,
        check=True,
    )

    # Use real Git
    git = RealGit()
    worktrees = git.list_worktrees(repo)

    assert len(worktrees) == 2
    assert any(wt.branch == "feature" for wt in worktrees)
```

### Dry-Run Test Pattern

```python
def test_dryrun_prevents_mutations() -> None:
    """Test dry-run mode prevents changes."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Use production context factory with dry_run=True
        ctx = create_context(dry_run=True)

        result = runner.invoke(
            cli,
            ["rm", "stack", "--force"],
            obj=ctx,
        )

        # Verify dry-run message printed
        assert "[DRY RUN]" in result.output or "[DRY RUN]" in result.stderr

        # Verify no actual changes (check filesystem)
        assert directory_still_exists
```

## CLI Testing Patterns

### When to Use CliRunner vs Subprocess

**Use CliRunner (preferred for command tests):**

- Testing Click command behavior (arguments, options, validation)
- Testing command output and exit codes
- Unit/integration testing of individual commands
- Any test that doesn't require true end-to-end CLI invocation

**Benefits:**

- Faster execution (no subprocess overhead)
- Better error messages (Python stack traces)
- Easier debugging (single process)
- Works with dependency injection and fakes

**Use subprocess (only for E2E tests):**

- Testing full CLI installation and packaging
- Testing shell integration (completion, environment)
- Verifying actual `uv run erk` behavior
- True end-to-end acceptance tests

**Benefits:**

- Tests real user experience
- Catches packaging and distribution issues
- Verifies shell environment handling

### CliRunner Pattern (PREFERRED)

#### Using erk_isolated_fs_env() (Recommended)

**For most CLI tests, use the `erk_isolated_fs_env()` helper:**

```python
from click.testing import CliRunner
from erk.cli.cli import cli
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.fakes.gitops import FakeGit
from erk.core.context import ErkContext
from erk.core.config_store import GlobalConfig

def test_create_command() -> None:
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up configuration and test context
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )
        global_config = GlobalConfig(
            erks_root=env.erks_root,
            use_graphite=False,
        )

        test_ctx = ErkContext.for_test(
            git=git,
            global_config=global_config,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["create", "feature-name"], obj=test_ctx)
        assert result.exit_code == 0
        assert "Created worktree" in result.output
```

**What `erk_isolated_fs_env()` provides:**

- `env.cwd`: Current working directory (root worktree)
- `env.git_dir`: Path to .git directory
- `env.root_worktree`: Root worktree with .git/ directory
- `env.erks_root`: Erks directory (parallel to root)
- `env.create_linked_worktree()`: Helper to create additional worktrees
- Automatic `runner.isolated_filesystem()` management
- Directory structure setup (repo/ and erks/ directories)

**Why use `erk_isolated_fs_env()`:**

- Complete isolation via `runner.isolated_filesystem()`
- Works with FakeGit (faster than real git)
- No HOME environment manipulation needed
- No manual directory changes or try/finally blocks
- Provides helpers for complex worktree scenarios

#### Using cli_test_repo() (For Real Git Operations)

**Only use `cli_test_repo()` when you need REAL git operations:**

```python
from click.testing import CliRunner
from erk.cli.cli import cli
from tests.test_utils.cli_helpers import cli_test_repo

def test_git_hook_integration(tmp_path: Path) -> None:
    with cli_test_repo(tmp_path) as test_env:
        # Set up CliRunner with isolated HOME
        env_vars = os.environ.copy()
        env_vars["HOME"] = str(test_env.tmp_path)
        runner = CliRunner(env=env_vars)

        # Run test from repo directory
        original_cwd = os.getcwd()
        try:
            os.chdir(test_env.repo)
            result = runner.invoke(cli, ["create", "feature-name", "--no-post"])
            assert result.exit_code == 0
            assert "Created worktree" in result.output
        finally:
            os.chdir(original_cwd)
```

**What `cli_test_repo()` provides:**

- `test_env.repo`: Real git repository with initial commit
- `test_env.erks_root`: Configured erks directory
- `test_env.tmp_path`: Test root with isolated .erk config

**When to use `cli_test_repo()` over `erk_isolated_fs_env()`:**

- Testing git hooks or git worktree edge cases
- Testing actual filesystem permissions
- Testing real subprocess interactions
- Integration tests requiring actual git behavior

**For 95% of CLI tests, use `erk_isolated_fs_env()` instead.**

#### Manual Setup (For Custom Requirements)

**When you need custom git state or special configuration, set up manually:**

```python
from click.testing import CliRunner
from erk.cli.cli import cli

def test_create_command(tmp_path: Path) -> None:
    # Set up isolated global config
    global_config_dir = tmp_path / ".erk"
    global_config_dir.mkdir()
    erks_root = tmp_path / "erks"
    (global_config_dir / "config.toml").write_text(
        f'erks_root = "{erks_root}"\nuse_graphite = false\n'
    )

    # Set up real git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create an initial commit
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    # Use CliRunner with isolated config
    env_vars = os.environ.copy()
    env_vars["HOME"] = str(tmp_path)
    runner = CliRunner(env=env_vars)

    original_cwd = os.getcwd()
    try:
        os.chdir(repo)
        result = runner.invoke(cli, ["create", "feature-name", "--no-post"])
        assert result.exit_code == 0
        assert "Created worktree" in result.output
    finally:
        os.chdir(original_cwd)
```

**Use manual setup when:**

- Testing with multiple worktrees pre-created
- Testing with specific branch configurations
- Testing with custom config settings
- Testing edge cases requiring non-standard git state

**Key components:**

**For `erk_isolated_fs_env()` pattern (recommended):**

- `runner = CliRunner()`: Click's test harness
- `erk_isolated_fs_env(runner)`: Context manager providing isolated environment
- `runner.invoke(cli, ["command"], obj=test_ctx)`: Pass context explicitly via `obj=`
- `result.exit_code`: Command exit code (0 = success)
- `result.output`: Combined stdout/stderr output
- Works with FakeGit for fast, isolated tests

**For `cli_test_repo()` pattern (real git only):**

- `CliRunner(env=env_vars)`: Click's test harness with isolated HOME
- `runner.invoke(cli, ["command", "args"])`: Invokes CLI group, which creates context naturally
- NO `obj=` parameter - let CLI create context from environment
- Manual `os.chdir()` with try/finally for working directory changes
- Uses real git commands via subprocess

### Subprocess Pattern (E2E ONLY)

**Only use for true end-to-end tests:**

```python
import subprocess

def test_cli_installation(tmp_path: Path) -> None:
    # Test actual CLI invocation
    result = subprocess.run(
        ["uv", "run", "erk", "create", "feature"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
```

**When subprocess is required:**

- Testing `uv run erk` actually works
- Verifying package installation
- Shell completion integration tests

### Common Mistakes

**❌ Using subprocess for command tests:**

```python
# SLOW - Spawns Python interpreter for each call
subprocess.run(["uv", "run", "erk", "create", "feature"])
```

**✅ Using CliRunner for command tests:**

```python
# FAST - Direct function call with Click harness
runner.invoke(cli, ["create", "feature"])
```

**❌ Using individual command imports:**

```python
# WRONG - Context not created properly
from erk.cli.commands.create import create
runner.invoke(create, ["feature"])  # AttributeError: 'NoneType' object has no attribute 'cwd'
```

**✅ Using cli group:**

```python
# CORRECT - CLI group creates context from environment
from erk.cli.cli import cli
runner.invoke(cli, ["create", "feature"])
```

**❌ Not using erk_isolated_fs_env():**

```python
# HARDER TO MAINTAIN - Manual setup with real git
runner = CliRunner()
# ... 20+ lines of git setup, config creation, env vars, os.chdir ...
```

**✅ Using erk_isolated_fs_env():**

```python
# CLEAN AND SIMPLE - Helper provides everything
runner = CliRunner()
with erk_isolated_fs_env(runner) as env:
    # Ready to test immediately
    git = FakeGit(git_common_dirs={env.cwd: env.git_dir})
    test_ctx = ErkContext.for_test(git=git, cwd=env.cwd)
```

### Migration Checklist

When converting tests from subprocess to CliRunner:

**Recommended approach (using erk_isolated_fs_env()):**

- [ ] Import `CliRunner` from `click.testing`
- [ ] Import `erk_isolated_fs_env` from `tests.test_utils.env_helpers`
- [ ] Import `cli` from `erk.cli.cli`
- [ ] Set up `runner = CliRunner()`
- [ ] Use `with erk_isolated_fs_env(runner) as env:` context manager
- [ ] Create `FakeGit` with `git_common_dirs={env.cwd: env.git_dir}`
- [ ] Create `ErkContext.for_test()` with fakes and `cwd=env.cwd`
- [ ] Replace `subprocess.run([...])` with `runner.invoke(cli, [...], obj=test_ctx)`
- [ ] Replace `result.returncode` with `result.exit_code`
- [ ] Replace stdout/stderr parsing with `result.output`
- [ ] Run tests and verify behavior with `pytest`

**Alternative approach (using cli_test_repo() for real git):**

- [ ] Import `CliRunner` from `click.testing`
- [ ] Import `cli_test_repo` from `tests.test_utils.cli_helpers`
- [ ] Import `cli` from `erk.cli.cli`
- [ ] Use `with cli_test_repo(tmp_path) as test_env:` context manager
- [ ] Set up isolated HOME with `env_vars["HOME"] = str(test_env.tmp_path)`
- [ ] Use `CliRunner(env=env_vars)` to isolate HOME directory
- [ ] Use `os.chdir()` with try/finally for working directory changes
- [ ] Replace `subprocess.run([...])` with `runner.invoke(cli, [...])`
- [ ] Run tests and verify behavior matches subprocess version

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Using mock.patch

```python
# DON'T DO THIS
def test_bad(monkeypatch):
    monkeypatch.setattr("module.function", lambda: "fake")
    result = function_under_test()
```

**Why it's bad**: Tight coupling to implementation details, fragile tests.

**Do this instead**:

```python
# DO THIS
def test_good():
    fake_ops = FakeShell(installed_tools={"tool": "/path"})
    ctx = ErkContext(..., shell=fake_ops, ...)
    result = function_under_test(ctx)
```

### ❌ Anti-Pattern 2: Mutating Private Attributes

```python
# DON'T DO THIS
def test_bad():
    ops = RealConfigStore()
    ops._path = test_path  # Violates encapsulation
```

**Do this instead**:

```python
# DO THIS
def test_good():
    ops = FakeConfigStore(...)  # Constructor injection
```

### ❌ Anti-Pattern 3: Not Using Context Injection

```python
# DON'T DO THIS
def test_bad():
    result = runner.invoke(cli, ["command"])  # Uses production context
```

**Do this instead**:

```python
# DO THIS
def test_good():
    test_ctx = create_test_context(...)  # Or ErkContext(...)
    result = runner.invoke(cli, ["command"], obj=test_ctx)
```

## When to Use Fakes vs Mocks

### Prefer Fakes (Default Approach)

Fakes simulate entire subsystems in-memory and are the preferred testing approach for erk.

**Benefits:**

- Enable comprehensive testing without external I/O (filesystem, subprocess, network)
- More maintainable than mocks (no brittle call assertions)
- Easier to understand (clear constructor parameters show test state)
- Support mutation tracking for asserting side effects
- Self-documenting test setup

**When to use fakes:**

- Testing CLI commands with git operations
- Testing configuration management
- Testing GitHub API interactions
- Testing Graphite workflows
- Testing shell completion generation
- Any scenario where you can model system behavior in-memory

**Example:**

```python
def test_with_fake():
    # Clear test setup: configure fake state via constructor
    completion = FakeCompletion(
        bash_script="# bash completion code",
        erk_path="/usr/local/bin/erk"
    )
    ctx = create_test_context(completion=completion)

    # Run command
    result = runner.invoke(completion_bash, obj=ctx)

    # Assert behavior via mutation tracking
    assert "bash" in completion.generation_calls
    assert "# bash completion code" in result.output
```

### When Mocks Make Sense

While fakes are preferred, mocking has legitimate use cases for scenarios that are difficult or impossible to fake.

**Acceptable use cases:**

1. **Error simulation** - Hardware failures, I/O errors that can't be faked
2. **Environment manipulation** - Testing behavior with specific environment variables
3. **Testing subprocess integration** - When verifying actual subprocess behavior matters
4. **External system edge cases** - Network timeouts, race conditions

**Example - Testing environment-specific behavior:**

```python
@patch.dict(os.environ, {"HOME": "/test/home"})
def test_home_directory_detection():
    # Testing that code correctly reads HOME variable
    result = detect_home_dir()
    assert result == Path("/test/home")
```

**Example - Testing subprocess error handling:**

```python
@patch("subprocess.run")
def test_subprocess_timeout(mock_run):
    # Simulating a subprocess timeout is hard to fake reliably
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=5)
    result = run_with_timeout()
    assert result.timed_out
```

### Decision Tree

```
Can you create a fake for this dependency?
├─ YES → Create/use a fake (preferred)
│  └─ Examples: Git, Completion, Shell
│
├─ NO → Consider if mocking is necessary
   ├─ Testing error edge cases? → Mock acceptable
   ├─ Testing environment behavior? → Mock acceptable
   ├─ Testing subprocess integration? → Mock acceptable
   └─ Otherwise → Reconsider if test is needed
```

### Migration Strategy

If you encounter existing tests using mocks:

1. **Evaluate**: Does an integration abstraction exist? (Git, Shell, etc.)
2. **If yes**: Refactor to use the fake implementation
3. **If no**: Consider creating an integration abstraction + fake if the mock is complex
4. **Keep mock only if**: It falls into acceptable use cases above

This codebase has successfully migrated from 100+ mock patches to fake-based testing. The completion tests (17 tests using `@patch`) were refactored to FakeCompletion, demonstrating this pattern.

## Real-World Refactoring Examples

### Example 1: Repository Discovery Without Patches

**❌ Before (using mock.patch):**

```python
from unittest.mock import patch
from erk.cli.core import RepoContext

def test_status_command(tmp_path: Path) -> None:
    git = FakeGit(git_common_dirs={tmp_path: tmp_path / ".git"})
    ctx = create_test_context(git=git)
    repo = RepoContext(root=tmp_path, repo_name="test-repo", erks_dir=tmp_path / "erks")

    runner = CliRunner()
    with patch("erk.cli.commands.status.discover_repo_context", return_value=repo):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(status_cmd, [], obj=ctx)
```

**✅ After (using cwd injection):**

```python
def test_status_command(tmp_path: Path) -> None:
    git = FakeGit(git_common_dirs={tmp_path: tmp_path / ".git"})
    ctx = create_test_context(
        git=git,
        cwd=tmp_path  # ← Set cwd to match git_common_dirs
    )

    runner = CliRunner()
    result = runner.invoke(status_cmd, [], obj=ctx)
```

**Key insight**: `discover_repo_context()` uses `ctx.git.get_git_common_dir(ctx.cwd)`, so configuring FakeGit with `git_common_dirs` and setting matching `cwd` allows discovery to work naturally without patching.

### Example 2: Path Mocking → Real File I/O with tmp_path

**❌ Before (using mock.patch.object):**

```python
from unittest.mock import patch
from pathlib import Path

def test_graphite_get_prs():
    fixture_data = '{"branches": [...]}'

    with patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "read_text", return_value=fixture_data):
        git = MagicMock()
        ops = RealGraphite()
        result = ops.get_prs_from_graphite(git, Path("/fake/repo"))
```

**✅ After (using tmp_path fixture):**

```python
def test_graphite_get_prs(tmp_path: Path):
    # Create real files in temp directory
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    pr_info_file = git_dir / ".graphite_pr_info"
    pr_info_file.write_text('{"branches": [...]}', encoding="utf-8")

    git = FakeGit(git_common_dirs={tmp_path: git_dir})
    ops = RealGraphite()
    result = ops.get_prs_from_graphite(git, tmp_path)
```

**Key insight**: Integration tests should use real file I/O with `tmp_path`, not Path mocking. This tests actual file reading behavior and ensures encoding is handled correctly.

**Files refactored**: `tests/integration/test_graphite.py` (20 patches/mocks eliminated)

### Example 3: Subprocess Mocks → Fake Abstractions

**❌ Before (using subprocess mock):**

```python
from unittest import mock

def test_create_uses_graphite():
    with mock.patch("subprocess.run") as mock_run:
        result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)
        # Fragile: relies on subprocess call implementation details
        assert any("gt" in str(call) for call in mock_run.call_args_list)
```

**✅ After (using FakeGraphite):**

```python
def test_create_without_graphite():
    # Test the non-graphite path (uses FakeGit successfully)
    graphite = FakeGraphite()
    ctx = create_test_context(git=git, graphite=graphite, graphite=False)

    result = runner.invoke(cli, ["create", "test-feature"], obj=ctx)
    # Clear assertion on actual behavior
    assert result.exit_code == 0
    assert "test-feature" in git.added_worktrees
```

**Key insight**: If command calls subprocess directly without abstraction, refactor tests to focus on paths that DO use abstractions, or test error handling before subprocess is reached.

**Files refactored**: `tests/commands/workspace/test_create.py` (2 patches eliminated)

### Example 4: Environment Variable Mocks → FakeShell

**❌ Before (using patch.dict):**

```python
from unittest.mock import patch
import os

def test_shell_detection_zsh():
    with patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
        ops = RealShell()
        result = ops.detect_shell()
        assert result == ("zsh", Path.home() / ".zshrc")
```

**✅ After (using FakeShell):**

```python
def test_shell_detection_zsh():
    shell = FakeShell(detected_shell=("zsh", Path.home() / ".zshrc"))
    ctx = create_test_context(shell=shell)

    result = runner.invoke(init_cmd, obj=ctx)
    assert "zsh" in result.output
```

**Key insight**: Use FakeShell for shell detection logic in unit tests. Keep integration tests with real environment for actual shell detection.

**Files refactored**: `tests/integration/test_shell.py` (5 patches eliminated)

### Example 5: When Mocks ARE Legitimate

Some mocks are legitimate and should NOT be replaced:

**✅ Legitimate Mock Usage:**

```python
# tests/commands/setup/test_init.py
from unittest import mock

def test_init_creates_global_config_first_time() -> None:
    """Test that init creates global config on first run.

    Mock usage here is LEGITIMATE:
    - os.environ HOME patch: Testing path resolution that depends on $HOME
    - Cannot fake environment variables (external boundary)
    - Patching HOME redirects Path.home() to test directory
    """
    with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
        result = runner.invoke(cli, ["init"], obj=test_ctx)
```

**Why these mocks are acceptable:**

1. Testing environment variable behavior (external boundary)
2. Cannot create an abstraction for `os.environ` (it's the OS interface)
3. Documented clearly in test file docstring
4. Used consistently across related tests

**Files with legitimate mocks**: `tests/commands/setup/test_init.py` (28 mocks, all documented)

## Migration Checklist

When refactoring tests from mocks to fakes:

- [ ] Check if integration abstraction exists (Git, Shell, Graphite, etc.)
- [ ] Replace mock setup with fake constructor injection
- [ ] Replace mock assertions with mutation tracking properties
- [ ] Set `cwd` in context to match fake configuration
- [ ] Use `tmp_path` for file operations instead of Path mocking
- [ ] Remove unused mock imports
- [ ] Run tests to verify behavior unchanged
- [ ] If mock remains, document why it's legitimate

## State Mutation in Fakes

### When Fakes Need Mutation

Some operations require mutating state to simulate external systems:

- Git operations (add/remove worktrees, checkout branches)
- Configuration updates (set values)

### Mutation vs Immutability

- **Initial State**: Always via constructor (immutable after construction)
- **Runtime State**: Modified through operation methods (mutable)
- **Mutation Tracking**: Exposed via read-only properties for assertions

### Example: Testing Mutations

```python
def test_branch_deletion():
    # Initial state via constructor
    git = FakeGit(
        worktrees={repo: [WorktreeInfo(path=wt, branch="feature")]},
        git_common_dirs={repo: repo / ".git"},
    )

    # Verify initial state
    assert len(git.list_worktrees(repo)) == 1

    # Perform mutation
    git.delete_branch_with_graphite(repo, "feature", force=True)

    # Verify mutation via tracking property
    assert "feature" in git.deleted_branches
    assert len(git.deleted_branches) == 1
```

## Decision Tree

```
Need to test CLI command?
├─ Unit test (fast, isolated logic)
│  └─ Use Fake* classes
│     └─ Configure state via constructor
│        └─ Inject via ErkContext
│           └─ Pass as obj= to runner.invoke()
│
└─ Integration test (verify real system behavior)
   └─ Use Real* classes
      └─ Set up with actual commands (git, etc.)
         └─ Use tmp_path for isolation
            └─ Verify actual filesystem/system changes
```

## Helper Functions

### create_test_context()

Located in `tests/fakes/context.py`:

```python
from tests.fakes.context import create_test_context

# Minimal context (all fakes with defaults)
ctx = create_test_context()

# Custom git
ctx = create_test_context(
    git=FakeGit(worktrees={...})
)

# Custom config_store
ctx = create_test_context(
    config_store=FakeConfigStore(
        erks_root=Path("<temp-dir>/ws")
    )
)

# Dry-run mode
ctx = create_test_context(dry_run=True)
```

## Common Test Fixtures

Recommended fixtures to add to `conftest.py`:

```python
@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Create a fake git repository for testing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    return repo

@pytest.fixture
def test_context() -> ErkContext:
    """Create minimal test context with all fakes."""
    return create_test_context()
```

## Summary

**Key Principles**:

1. Use ABC-based interfaces (not Protocol)
2. Inject dependencies through constructor (no mutation after creation, except for state-tracking operations)
3. Three implementations: Real, Dry-Run (for writes), Fake (for tests)
4. No mock.patch or monkeypatch (except documented edge cases)
5. Unit tests use Fakes, Integration tests use Reals
6. Mutation tracking via read-only properties

**When in Doubt**:

- Use `create_test_context()` helper
- Configure fakes via constructor parameters
- Inject via `obj=test_ctx` to Click commands
- Assert on results and mutation tracking properties
