# Plan: Add `-f`/`--force` Flag to `erk plan submit` for TUI Support

> **Replans:** #5729

## What Changed Since Original Plan

No significant codebase changes. The original plan remains fully valid. This replan confirms current line numbers and provides refined implementation details.

## Investigation Findings

### Current State Confirmed

| Component | Status | Location |
|-----------|--------|----------|
| `submit_cmd` force flag | NOT IMPLEMENTED | `src/erk/cli/commands/submit.py:793-802` |
| `_prompt_existing_branch_action` force param | NOT IMPLEMENTED | `src/erk/cli/commands/submit.py:107-140` |
| `_validate_issue_for_submit` force param | NOT IMPLEMENTED | `src/erk/cli/commands/submit.py:295-364` |
| TUI submit invocation `-f` | NOT IMPLEMENTED | `src/erk/tui/screens/plan_detail_screen.py:676` |
| Provider submit invocation `-f` | NOT IMPLEMENTED | `src/erk/tui/data/provider.py:378` |
| Force mode tests | NOT IMPLEMENTED | `tests/commands/submit/test_existing_branch_detection.py` |

### Blocking Operations Identified

Two `ctx.console.confirm()` calls block TUI execution:
- Line 130: `ctx.console.confirm(f"Use existing branch '{branch_to_use}'?", default=True)`
- Line 133: `ctx.console.confirm("Delete existing branch(es) and create new?", default=False)`

## Implementation Steps

### 1. Add `--force` flag to `submit_cmd`

**File:** `src/erk/cli/commands/submit.py`

Add option after `--base` (around line 800):

```python
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Delete existing branches and create fresh without prompting.",
)
```

Update function signature at line 802:
```python
def submit_cmd(ctx: ErkContext, issue_numbers: tuple[int, ...], base: str | None, force: bool) -> None:
```

### 2. Add `force` parameter to `_validate_issue_for_submit`

**File:** `src/erk/cli/commands/submit.py` (lines 295-300)

```python
def _validate_issue_for_submit(
    ctx: ErkContext,
    repo: RepoContext,
    issue_number: int,
    base_branch: str,
    *,
    force: bool,  # Add keyword-only parameter
) -> ValidatedIssue:
```

At line 354, pass force to `_prompt_existing_branch_action`:
```python
if existing_branches:
    chosen = _prompt_existing_branch_action(
        ctx, repo.root, existing_branches, new_branch_name, force=force
    )
```

### 3. Add `force` parameter to `_prompt_existing_branch_action`

**File:** `src/erk/cli/commands/submit.py` (lines 107-112)

```python
def _prompt_existing_branch_action(
    ctx: ErkContext,
    repo_root: Path,
    existing_branches: list[str],
    new_branch_name: str,
    *,
    force: bool,  # Add keyword-only parameter
) -> str | None:
```

Add force mode logic at the start of function (after docstring, before line 122):
```python
    if force:
        user_output(f"\nDeleting {len(existing_branches)} existing branch(es) (--force mode):")
        for branch in existing_branches:
            ctx.branch_manager.delete_branch(repo_root, branch, force=True)
            user_output(f"  Deleted: {branch}")
        return None  # Signal "create new branch"
```

### 4. Pass `force` through call chain in `submit_cmd`

**File:** `src/erk/cli/commands/submit.py`

Find the call to `_validate_issue_for_submit` (around line 895) and pass `force`:
```python
validated = _validate_issue_for_submit(ctx, repo, issue_number, base_branch, force=force)
```

### 5. Add `-f` to TUI invocations

**File:** `src/erk/tui/screens/plan_detail_screen.py` (line 676)

Change:
```python
["erk", "plan", "submit", str(row.issue_number)]
```
To:
```python
["erk", "plan", "submit", str(row.issue_number), "-f"]
```

**File:** `src/erk/tui/data/provider.py` (line 378)

Change:
```python
["erk", "plan", "submit", str(issue_number)]
```
To:
```python
["erk", "plan", "submit", str(issue_number), "-f"]
```

### 6. Add tests for force mode

**File:** `tests/commands/submit/test_existing_branch_detection.py`

Add two new tests:

```python
def test_submit_force_deletes_existing_branches_and_creates_new(tmp_path: Path) -> None:
    """Test --force deletes existing branches without prompting."""
    # Setup with existing P123-* branch
    # Invoke with "-f" flag
    # Assert: no confirm() calls, branch deleted, new branch created


def test_submit_force_creates_new_branch_when_none_exist(tmp_path: Path) -> None:
    """Test --force creates new branch normally when no existing branches."""
    # Setup without existing P123-* branches
    # Invoke with "-f" flag
    # Assert: normal flow, new branch created
```

## Files to Modify

1. `src/erk/cli/commands/submit.py` - Add flag and force parameters
2. `src/erk/tui/screens/plan_detail_screen.py` - Add `-f` to command
3. `src/erk/tui/data/provider.py` - Add `-f` to command
4. `tests/commands/submit/test_existing_branch_detection.py` - Add force mode tests

## Verification

1. **Unit tests:**
   ```bash
   uv run pytest tests/commands/submit/test_existing_branch_detection.py -v
   ```

2. **Manual CLI test:**
   ```bash
   # Create a branch matching P{issue}-* pattern first, then:
   erk plan submit <issue_number> -f
   # Verify: deletes existing branch, creates new one, no prompts
   ```

3. **TUI test:**
   - Open TUI: `erk dash -i`
   - Select a plan with existing P{issue}-* branch
   - Run "Submit to Queue" action
   - Verify: no "Aborted!", clean execution

## Related Documentation

- `dignified-python` skill - Keyword-only parameters
- `fake-driven-testing` skill - Test patterns with FakeConsole
- `docs/learned/tripwires.md` - Force flag `-f` convention