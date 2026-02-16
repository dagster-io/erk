---
title: Exec Script Testing Patterns
last_audited: "2026-02-16 00:00 PT"
audit_result: edited
read_when:
  - "testing exec CLI commands"
  - "writing integration tests for scripts"
  - "debugging 'Context not initialized' errors in tests"
  - "debugging flaky tests in parallel execution"
tripwires:
  - action: "using monkeypatch.chdir() in exec script tests"
    warning: "Use obj=ErkContext.for_test(cwd=tmp_path) instead. monkeypatch.chdir() doesn't inject context, causing 'Context not initialized' errors."
    pattern: "monkeypatch\\.chdir\\("
  - action: "testing code that reads from Path.home() or ~/.claude/ or ~/.erk/"
    warning: "Tests that run in parallel must use monkeypatch to isolate from real filesystem state. Functions like extract_slugs_from_session() cause flakiness when they read from the user's home directory."
    pattern: "Path\\.home\\(\\)"
  - action: "using Path.home() directly in production code"
    warning: "Use gateway abstractions instead. For ~/.claude/ paths use ClaudeInstallation, for ~/.erk/ paths use ErkInstallation. Direct Path.home() access bypasses testability (fakes) and creates parallel test flakiness."
    pattern: "Path\\.home\\(\\)"
---

# Exec Script Testing Patterns

Testing patterns for CLI commands in `src/erk/cli/commands/exec/scripts/`.

## Required Pattern: Context Injection

All exec script tests MUST use `ErkContext.for_test()` for dependency injection:

```python
from click.testing import CliRunner
from erk_shared.context.context import ErkContext
from erk.cli.commands.exec.scripts.my_command import my_command

def test_my_command(tmp_path: Path) -> None:
    """Test using context injection."""
    runner = CliRunner()
    result = runner.invoke(
        my_command,
        ["--json"],
        obj=ErkContext.for_test(cwd=tmp_path),  # REQUIRED
    )
    assert result.exit_code == 0
```

## Anti-Pattern: monkeypatch.chdir()

Do NOT use `monkeypatch.chdir()` for exec script tests:

```python
# WRONG - Causes "Context not initialized" error
def test_my_command_wrong(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)  # This doesn't inject context!

    runner = CliRunner()
    result = runner.invoke(my_command, ["--json"])
    # FAILS: "Error: Context not initialized"
```

## Why Context Injection?

Exec scripts use `require_cwd(ctx)` and similar helpers that read from `ctx.obj`:

```python
@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    cwd = require_cwd(ctx)  # Reads from ctx.obj.cwd
```

When you use `monkeypatch.chdir()`:

- The process working directory changes
- But `ctx.obj` remains `None`
- `require_cwd(ctx)` fails with "Context not initialized"

When you use `obj=ErkContext.for_test(cwd=...)`:

- The context is properly injected
- `ctx.obj` contains the `ErkContext` instance
- `require_cwd(ctx)` returns the test path

## Sharing Context Across Multiple Invocations

When testing multiple commands in sequence, reuse the same context:

```python
def test_multiple_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    ctx = ErkContext.for_test(cwd=tmp_path)  # Create once

    # First command
    result1 = runner.invoke(command1, ["arg"], obj=ctx)
    assert result1.exit_code == 0

    # Second command (same context)
    result2 = runner.invoke(command2, ["arg"], obj=ctx)
    assert result2.exit_code == 0
```

## Available Context Helpers

From `erk_shared.context.helpers`:

| Helper                   | Returns        | Usage                     |
| ------------------------ | -------------- | ------------------------- |
| `require_cwd(ctx)`       | `Path`         | Current working directory |
| `require_repo_root(ctx)` | `Path`         | Repository root path      |
| `require_git(ctx)`       | `Git`          | Git operations            |
| `require_github(ctx)`    | `GitHub`       | GitHub operations         |
| `require_issues(ctx)`    | `GitHubIssues` | GitHub issues operations  |

## Test File Locations

- **Integration tests**: `tests/integration/cli/commands/exec/scripts/`
- **Unit tests**: `tests/unit/cli/commands/exec/scripts/`

## Pattern: Parameterizing Path.home() for Testability

When functions need home directory paths (for `~/.claude/`, `~/.ssh/`, etc.), use this pattern to maintain testability.

### The Problem

```python
# BAD - Not testable, triggers tripwire
def build_docker_run_args(worktree_path: Path) -> list[str]:
    claude_dir = Path.home() / ".claude"  # Hardcoded!
    ...
```

### The Solution

Make `home_dir` a **required parameter** with no default/fallback:

```python
# GOOD - Testable function
def build_docker_run_args(
    *,
    worktree_path: Path,
    image_name: str,
    interactive: bool,
    home_dir: Path,  # Required, no fallback
) -> list[str]:
    claude_dir = home_dir / ".claude"
    ssh_dir = home_dir / ".ssh"
    ...
```

### CLI Boundary

Call `Path.home()` only in CLI-layer functions that can't be unit tested anyway (e.g., functions using `os.execvp` or subprocess):

```python
# CLI-layer function - acceptable to use Path.home() here
def execute_docker_interactive(...) -> None:
    docker_args = build_docker_run_args(
        worktree_path=worktree_path,
        image_name=image_name,
        interactive=True,
        home_dir=Path.home(),  # At CLI boundary
    )
    os.execvp("docker", docker_args)  # Can't unit test anyway
```

### Testing

Tests pass `tmp_path` for the home directory:

```python
def test_build_docker_run_args_mounts_claude_dir(tmp_path: Path) -> None:
    # Create fake home structure
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    args = build_docker_run_args(
        worktree_path=Path("/path/to/worktree"),
        image_name="erk-local:latest",
        interactive=True,
        home_dir=tmp_path,  # Test with tmp_path
    )

    # Verify mount includes fake home path
    assert any(str(claude_dir) in arg for arg in args)
```

### Why No Default?

Using `home_dir: Path | None = None` with fallback `Path.home()` still triggers the tripwire because the fallback executes in the function body. Making the parameter required:

1. Forces CLI code to explicitly provide `Path.home()`
2. Makes the testability boundary clear
3. Prevents accidental use of real home in tests

**Principle**: Make `home_dir` a required parameter in any function that needs home directory paths. Call `Path.home()` only at the CLI boundary.

## Testing Branch Operations

When testing exec scripts that create and checkout branches, use `FakeBranchManager` to verify the operation sequence.

### Pattern: Verify create_branch + checkout_branch Sequence

`FakeBranchManager` is located at `erk_shared.gateway.branch_manager.fake`. It tracks branch operations via internal lists exposed as read-only properties:

- `created_branches` - list of `(branch_name, base_branch)` tuples
- `checked_out_branches` - list of branch names
- `tracked_branches` - list of `(branch_name, parent_branch)` tuples

```python
from erk_shared.gateway.branch_manager.fake import FakeBranchManager

# Create a FakeBranchManager
fake_branch_manager = FakeBranchManager()

# After running a command that creates and checks out a branch:
# Verify branch was created
assert any("P123-" in name for name, _ in fake_branch_manager.created_branches)
# Verify branch was checked out
assert any("P123-" in name for name in fake_branch_manager.checked_out_branches)
```

Note: `context_for_test()` (from `erk.core.context`) does not accept a `branch_manager` parameter directly. Branch manager is derived from the `ErkContext` based on git/graphite configuration.

### Why This Matters

GraphiteBranchManager.create_branch() restores the original branch after Graphite tracking. Tests must verify that commands explicitly call checkout_branch() afterward, or they'll silently end up on the wrong branch.

## Testing Idempotent Commands

Commands that support `--session-id` for deduplication need tests verifying idempotency behavior.

### Pattern: Two Sequential Invocations

```python
def test_command_is_idempotent_within_session(tmp_path: Path) -> None:
    """Verify second invocation returns skipped_duplicate."""
    runner = CliRunner()
    ctx = ErkContext.for_test(cwd=tmp_path)
    session_id = "test-session-123"

    # First invocation - executes normally
    result1 = runner.invoke(
        my_command,
        ["--session-id", session_id, "--format", "json"],
        obj=ctx,
    )
    assert result1.exit_code == 0
    data1 = json.loads(result1.output)
    assert data1.get("skipped_duplicate") is not True  # First run executes

    # Second invocation - should be deduplicated
    result2 = runner.invoke(
        my_command,
        ["--session-id", session_id, "--format", "json"],
        obj=ctx,
    )
    assert result2.exit_code == 0
    data2 = json.loads(result2.output)
    assert data2.get("skipped_duplicate") is True  # Second run skipped
```

### Assertions to Verify

1. **First invocation**: `skipped_duplicate` is `False` or absent
2. **Second invocation**: `skipped_duplicate` is `True`
3. **Exit code**: Both invocations succeed (exit code 0)
4. **Side effects**: Only the first invocation creates resources

### Format-Specific Testing

Some commands have different output formats. Test idempotency in both:

```python
@pytest.mark.parametrize("format_flag", ["--format=json", "--format=text"])
def test_idempotency_all_formats(format_flag: str, tmp_path: Path) -> None:
    # Test with each output format
    ...
```

## Migrating Tests for Discriminated Union Returns

When a gateway method changes from exception-based to discriminated union (e.g., `T | ErrorType`), update exec script tests to check return types instead of catching exceptions.

### Key Differences

| Aspect              | Exception-Based                     | Discriminated Union                     |
| ------------------- | ----------------------------------- | --------------------------------------- |
| Fake setup          | Set error flag, fake raises         | Configure fake to return error type     |
| Gateway behavior    | `raise SomeError()`                 | `return SomeErrorSentinel(...)`         |
| Exec script pattern | `try/except` block                  | `if isinstance(result, ErrorSentinel):` |
| Test assertion      | Verify exception caught & formatted | Verify error type returned & formatted  |

### Real Example: IssueNotFound

The `IssueNotFound` sentinel (`erk_shared.gateway.github.issues.types`) is used in union return types. `FakeGitHubIssues` handles this by returning `IssueNotFound` when the requested issue number is not in its `issues` dict, rather than raising an exception.

```python
# FakeGitHubIssues constructor configures known issues:
fake_issues = FakeGitHubIssues(issues={42: some_issue_info})

# When code requests issue 999, the fake returns IssueNotFound
# The exec script checks: if isinstance(result, IssueNotFound): ...
```

### Migration Checklist

When migrating exec script tests for discriminated unions:

1. [ ] Update fake setup to return error types instead of raising
2. [ ] Update exec script to use `isinstance()` checks instead of `try/except`
3. [ ] Verify test still checks exit code and error message
4. [ ] Verify test covers both success and error paths
5. [ ] Update test names if needed (e.g., `test_issue_not_found_exception` → `test_issue_not_found`)

## Testing Interactive/NoReturn Gateway Methods

Some gateway methods are `NoReturn` - they call `os.exec*()` to replace the current process (e.g., `exec_ssh_interactive()`). These methods never return control to the caller.

### Problem

Methods with `NoReturn` type annotation never return. Testing them directly would cause the test process to be replaced.

### Solution Pattern

**DO NOT call the method directly.** Instead:

1. Verify the fake gateway recorded the call
2. Check the call parameters (interactive=True, correct command, etc.)
3. No assertions after the call - they won't execute

### Example: Testing exec_ssh_interactive

**From:** `tests/unit/cli/commands/codespace/run/objective/test_next_plan_cmd.py`

```python
from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.gateway.codespace.fake import FakeCodespace
from erk_shared.gateway.codespace_registry.fake import FakeCodespaceRegistry

def test_run_next_plan_starts_codespace_and_runs_command() -> None:
    """run objective next-plan starts the codespace and runs the command."""
    runner = CliRunner()

    cs = _make_codespace("mybox")
    fake_codespace = FakeCodespace()
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    ctx = context_for_test(codespace=fake_codespace, codespace_registry=codespace_registry)

    result = runner.invoke(
        cli,
        ["codespace", "run", "objective", "next-plan", "42"],
        obj=ctx,
        catch_exceptions=False,
    )

    # Verify start_codespace was called
    assert fake_codespace.started_codespaces == ["user-mybox-abc123"]

    # Verify exec_ssh_interactive was called with correct parameters
    assert fake_codespace.exec_called is True
    assert len(fake_codespace.ssh_calls) == 1
    call = fake_codespace.ssh_calls[0]
    assert call.gh_name == "user-mybox-abc123"
    assert "erk objective next-plan 42" in call.remote_command
    assert call.interactive is True
```

**Key points:**

- `exec_called` attribute tracks whether `exec_ssh_interactive()` was invoked
- `ssh_calls` list stores parameters passed to the call
- `interactive` field distinguishes `exec_ssh_interactive()` from `run_ssh_command()`

### Why This Works

**FakeCodespace behavior:**

- `exec_ssh_interactive()` records the call and returns normally (doesn't actually exec)
- Real gateway would replace process, test never reaches assertions
- Fake gateway lets test continue and verify the call parameters

### Gotcha: No Code After exec_ssh_interactive

In real code, nothing after `exec_ssh_interactive()` executes:

```python
# Command implementation
def next_plan(ctx: ErkContext, issue_ref: str) -> None:
    codespace.exec_ssh_interactive(gh_name, remote_command)
    # THIS LINE NEVER RUNS - process was replaced
    print("Done")  # Dead code
```

**In tests:** The fake lets execution continue, but this doesn't match production behavior. Don't write tests that depend on post-exec code running.

### Verification Checklist

When testing NoReturn gateway methods:

- ✅ Verify `exec_called is True`
- ✅ Check parameters in the call record (`ssh_calls`, `gh_name`, `remote_command`, `interactive`)
- ✅ Verify command arguments are correctly formatted
- ❌ Don't assert on return values (there are none)
- ❌ Don't write code that depends on execution continuing after the call

### Related Gateway Methods

Other `NoReturn` methods that follow this pattern:

- `exec_ssh_interactive()` - Replace process with SSH command
- `os.execvp()` - Replace process with any command

See [SSH Command Execution](../architecture/ssh-command-execution.md) for when to use `exec_ssh_interactive()` vs `run_ssh_command()`.

## Empty String Normalization for JSON Output

When a CLI parameter receives `""` (empty string) to clear a value, normalize to `None` before JSON output. This ensures JSON consumers see `null` rather than `""`, which has different semantics.

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, _build_output -->

The pattern converts each value using a falsy check: if the string is empty (or falsy), substitute `None`; otherwise keep the original value. Apply this to each field that may receive `""` before building the JSON output dict.

<!-- See source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py:183-185 -->

**Why normalize?** Empty string (`""`) and absent (`None`/`null`) have different meanings in JSON:

- `""` — value was explicitly set to empty
- `null` — value was cleared or never set

For "clear this field" operations, `null` is the correct JSON representation.

## Related Documentation

- [CLI Testing Patterns](cli-testing.md) - General CLI testing patterns
- [SSH Command Execution](../architecture/ssh-command-execution.md) - Decision framework for SSH methods
- Source: `src/erk/cli/commands/exec/scripts/AGENTS.md` - Exec script standards
