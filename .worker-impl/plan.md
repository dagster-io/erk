# Migrate GraphiteGtKit Methods to Graphite and Delete GraphiteGtKit

## Summary

Migrate the remaining 2 methods from `GraphiteGtKit` (`squash_commits()` and `submit()`) to the `Graphite` interface with new names (`squash_branch()` and `submit_stack()`), update all call sites, then delete the `GraphiteGtKit` interface entirely.

## Design Decisions

- **Return type**: Void + exceptions (following Graphite's existing pattern)
- **Method names**: `squash_branch()` and `submit_stack()` (explicit names)
- **Error handling**: Raise `RuntimeError` on failure via `run_subprocess_with_context()`

## Implementation Steps

### Step 1: Add New Methods to Graphite ABC

**File:** `packages/erk-shared/src/erk_shared/integrations/graphite/abc.py`

Add two new abstract methods:

```python
@abstractmethod
def squash_branch(self, repo_root: Path, *, quiet: bool = False) -> None:
    """Squash all commits on the current branch into one.

    Uses `gt squash` to consolidate commits. This is typically called
    before submitting a PR to create a clean single-commit branch.

    Args:
        repo_root: Repository root directory
        quiet: If True, suppress output

    Raises:
        RuntimeError: If gt squash fails
    """
    ...

@abstractmethod
def submit_stack(
    self, repo_root: Path, *, publish: bool = False, restack: bool = False, quiet: bool = False
) -> None:
    """Submit the current stack to create or update PRs.

    Uses `gt submit` to push branches and create/update GitHub PRs.
    This differs from submit_branch() which only pushes a single branch
    without PR creation.

    Args:
        repo_root: Repository root directory
        publish: If True, mark PRs as ready for review (not draft)
        restack: If True, restack before submitting
        quiet: If True, suppress output

    Raises:
        RuntimeError: If gt submit fails or times out
    """
    ...
```

### Step 2: Implement in RealGraphite

**File:** `packages/erk-shared/src/erk_shared/integrations/graphite/real.py`

```python
def squash_branch(self, repo_root: Path, *, quiet: bool = False) -> None:
    """Squash all commits on the current branch into one."""
    cmd = ["gt", "squash", "--no-edit", "--no-interactive"]

    run_subprocess_with_context(
        cmd,
        operation_context="squash branch commits with Graphite",
        cwd=repo_root,
        stdout=DEVNULL if quiet else sys.stdout,
        stderr=subprocess.PIPE,
    )

def submit_stack(
    self, repo_root: Path, *, publish: bool = False, restack: bool = False, quiet: bool = False
) -> None:
    """Submit the current stack to create or update PRs."""
    cmd = ["gt", "submit", "--no-edit", "--no-interactive"]

    if publish:
        cmd.append("--publish")
    if restack:
        cmd.append("--restack")

    # Use 120-second timeout for network operations
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            timeout=120,
            stdout=DEVNULL if quiet else sys.stdout,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        if not quiet and result.stderr:
            user_output(result.stderr, nl=False)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            "gt submit timed out after 120 seconds. Check network connectivity and try again."
        ) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"gt submit failed (exit code {e.returncode}): {e.stderr or ''}"
        ) from e
```

### Step 3: Implement in FakeGraphite

**File:** `packages/erk-shared/src/erk_shared/integrations/graphite/fake.py`

Add to `__init__`:
```python
self._squash_branch_raises: Exception | None = None
self._squash_branch_calls: list[tuple[Path, bool]] = []
self._submit_stack_raises: Exception | None = None
self._submit_stack_calls: list[tuple[Path, bool, bool, bool]] = []
```

Add methods:
```python
def squash_branch(self, repo_root: Path, *, quiet: bool = False) -> None:
    """Track squash_branch calls and optionally raise."""
    self._squash_branch_calls.append((repo_root, quiet))
    if self._squash_branch_raises is not None:
        raise self._squash_branch_raises

def submit_stack(
    self, repo_root: Path, *, publish: bool = False, restack: bool = False, quiet: bool = False
) -> None:
    """Track submit_stack calls and optionally raise."""
    self._submit_stack_calls.append((repo_root, publish, restack, quiet))
    if self._submit_stack_raises is not None:
        raise self._submit_stack_raises

@property
def squash_branch_calls(self) -> list[tuple[Path, bool]]:
    """Get the list of squash_branch() calls."""
    return self._squash_branch_calls

@property
def submit_stack_calls(self) -> list[tuple[Path, bool, bool, bool]]:
    """Get the list of submit_stack() calls."""
    return self._submit_stack_calls
```

### Step 4: Implement in DryRunGraphite

**File:** `packages/erk-shared/src/erk_shared/integrations/graphite/dry_run.py`

```python
def squash_branch(self, repo_root: Path, *, quiet: bool = False) -> None:
    """No-op for gt squash in dry-run mode."""
    pass

def submit_stack(
    self, repo_root: Path, *, publish: bool = False, restack: bool = False, quiet: bool = False
) -> None:
    """No-op for gt submit in dry-run mode."""
    pass
```

### Step 5: Update Call Sites

Update 3 command files to use `ops.main_graphite()` instead of `ops.graphite()`:

**File 1:** `packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/submit_branch.py`

- Line 328: Change `result = ops.graphite().squash_commits()` to:
  ```python
  ops.main_graphite().squash_branch(repo_root, quiet=False)
  ```
  Remove the `if not result.success` error handling (now exception-based).

- Line 444: Change `result_holder.append(ops.graphite().submit(...))` to:
  ```python
  ops.main_graphite().submit_stack(repo_root, publish=True, restack=False, quiet=False)
  ```
  Wrap in try/except if needed for error display.

**File 2:** `packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/simple_submit.py`

- Line 255: Change `squash_result = ops.graphite().squash_commits()` to:
  ```python
  ops.main_graphite().squash_branch(repo_root, quiet=False)
  ```

- Line 270: Change `result = ops.graphite().submit(publish=True, restack=True)` to:
  ```python
  ops.main_graphite().submit_stack(repo_root, publish=True, restack=True, quiet=False)
  ```

**File 3:** `packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/pr_update.py`

- Line 75: Change `result = ops.graphite().submit(publish=True, restack=False)` to:
  ```python
  ops.main_graphite().submit_stack(repo_root, publish=True, restack=False, quiet=False)
  ```

### Step 6: Delete GraphiteGtKit Infrastructure

**Delete from ABC:**
- `packages/erk-shared/src/erk_shared/integrations/gt/abc.py`:
  - Remove `GraphiteGtKit` class (lines 169-190)
  - Remove `graphite()` method from `GtKit` ABC (lines 341-346)
  - Remove `CommandResult` import if no longer used

**Delete implementations:**
- `packages/erk-shared/src/erk_shared/integrations/gt/real.py`:
  - Remove `RealGraphiteGtKit` class (lines 252-297)
  - Remove `_graphite` field and `graphite()` method from `RealGtKit`

- `packages/erk-shared/src/erk_shared/integrations/gt/fake.py`:
  - Remove `GraphiteState` dataclass (lines 35-53)
  - Remove `FakeGraphiteGtKitOps` class (lines 183-213)
  - Remove `_graphite` field and `graphite()` method from `FakeGtKitOps`
  - Remove declarative setup methods: `with_squash_failure()`, `with_submit_failure()`, `with_submit_success_but_nothing_submitted()`, `with_restack_failure()`

**Delete exports:**
- `packages/erk-shared/src/erk_shared/integrations/gt/__init__.py`:
  - Remove `GraphiteGtKit` from exports
  - Remove `GraphiteState` from exports
  - Remove `FakeGraphiteGtKitOps` from exports

- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/ops.py`:
  - Remove re-exports of deleted classes

**Delete types if unused:**
- `packages/erk-shared/src/erk_shared/integrations/gt/types.py`:
  - Check if `CommandResult` is still used elsewhere; if not, delete it

### Step 7: Update Tests

**Unit tests to update:**

1. `packages/dot-agent-kit/tests/unit/kits/gt/test_submit_branch.py`:
   - Update to use `FakeGraphite` configuration instead of `FakeGtKitOps.with_squash_failure()`
   - Test exception handling instead of `CommandResult.success` checks

2. `packages/dot-agent-kit/tests/unit/kits/gt/test_simple_submit.py`:
   - Same pattern as above

3. `packages/dot-agent-kit/tests/unit/kits/gt/test_pr_update.py`:
   - Update submit tests to use new pattern

4. `packages/dot-agent-kit/tests/unit/kits/gt/test_real_ops.py`:
   - Remove tests for `RealGraphiteGtKit`
   - Add tests for `RealGraphite.squash_branch()` and `submit_stack()` if not already covered

5. `packages/dot-agent-kit/tests/unit/kits/gt/fake_ops.py`:
   - Remove `GraphiteState` usage
   - Update to use `FakeGraphite` for graphite operations

## Files to Modify

| File | Action |
|------|--------|
| `packages/erk-shared/src/erk_shared/integrations/graphite/abc.py` | Add 2 methods |
| `packages/erk-shared/src/erk_shared/integrations/graphite/real.py` | Add 2 methods |
| `packages/erk-shared/src/erk_shared/integrations/graphite/fake.py` | Add 2 methods + tracking |
| `packages/erk-shared/src/erk_shared/integrations/graphite/dry_run.py` | Add 2 no-op methods |
| `packages/erk-shared/src/erk_shared/integrations/gt/abc.py` | Delete GraphiteGtKit |
| `packages/erk-shared/src/erk_shared/integrations/gt/real.py` | Delete RealGraphiteGtKit |
| `packages/erk-shared/src/erk_shared/integrations/gt/fake.py` | Delete FakeGraphiteGtKitOps |
| `packages/erk-shared/src/erk_shared/integrations/gt/__init__.py` | Update exports |
| `packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/submit_branch.py` | Update calls |
| `packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/simple_submit.py` | Update calls |
| `packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/pr_update.py` | Update calls |
| `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/ops.py` | Update re-exports |
| `packages/dot-agent-kit/tests/unit/kits/gt/test_submit_branch.py` | Update tests |
| `packages/dot-agent-kit/tests/unit/kits/gt/test_simple_submit.py` | Update tests |
| `packages/dot-agent-kit/tests/unit/kits/gt/test_pr_update.py` | Update tests |
| `packages/dot-agent-kit/tests/unit/kits/gt/test_real_ops.py` | Update/remove tests |

## Verification

After implementation:
1. Run `uv run pytest packages/dot-agent-kit/tests/unit/kits/gt/` - all GT kit tests pass
2. Run `uv run pyright packages/erk-shared packages/dot-agent-kit` - no type errors
3. Run `uv run ruff check packages/erk-shared packages/dot-agent-kit` - no lint errors
4. Verify no remaining references to `GraphiteGtKit` in codebase