# Plan: Migrate admin.py to Ensure-Based Error Handling

**Part of Objective #5185, Step 1C.2**

## Context

Objective #5185 systematically migrates CLI `user_output() + SystemExit(1)` patterns to use the `Ensure` class for consistent error handling. Phase 1A (steelthread) and 1B (high-count files) are complete. This is Phase 1C step 2: migrating `admin.py` which has 8 patterns.

## Pattern Analysis

`src/erk/cli/commands/admin.py` has 8 `SystemExit(1)` patterns across 3 commands:

### Group A: `Ensure.not_none()` migrations (4 patterns)

| Location | Command | Current check | Notes |
|----------|---------|---------------|-------|
| L53-56 | `github_pr_setting` | `repo.github is None` | Multi-line message (2 lines) |
| L181-183 | `test_plan_implement_gh_workflow` | `repo.github is None` | Single-line message |
| L189-191 | `test_plan_implement_gh_workflow` | `current_branch is None` | Single-line message |
| L257-259 | `test_plan_implement_gh_workflow` | `username is None` | Single-line message |

### Group B: `Ensure.invariant()` migration (1 pattern)

| Location | Command | Current check | Notes |
|----------|---------|---------------|-------|
| L140-145 | `upgrade_repo` | `not erk_dir.exists()` | Multi-line message (3 lines); NOT `Ensure.path_exists()` since `.erk/` is not a git-managed path |

### Group C: `UserFacingCliError` direct (3 patterns)

| Location | Command | Current pattern | Notes |
|----------|---------|-----------------|-------|
| L92-94 | `github_pr_setting` | `except RuntimeError` | Cannot use Ensure (exception catch, not condition check) |
| L107-109 | `github_pr_setting` | `except RuntimeError` | Same |
| L121-124 | `github_pr_setting` | `except RuntimeError` | Same |

These 3 are NOT Ensure candidates per the migration decision tree ("no clear boolean condition"). Instead, replace the manual `user_output(click.style("Error: "...)) + raise SystemExit(1)` with `raise UserFacingCliError(str(e)) from e`, which handles styling internally.

## Implementation

### Step 1: Update imports

In `src/erk/cli/commands/admin.py`, add `Ensure` to the existing ensure import:

```python
# Before:
from erk.cli.ensure import UserFacingCliError

# After:
from erk.cli.ensure import Ensure, UserFacingCliError
```

### Step 2: Migrate `github_pr_setting` (4 patterns)

**Pattern 1 (L53-56):** `repo.github is None` with multi-line message

```python
# Before:
if repo.github is None:
    user_output(click.style("Error: ", fg="red") + "Not a GitHub repository")
    user_output("This command requires the repository to have a GitHub remote configured.")
    raise SystemExit(1)

# After:
Ensure.not_none(
    repo.github,
    "Not a GitHub repository\n"
    "This command requires the repository to have a GitHub remote configured.",
)
```

**Patterns 2-4 (L92-94, L107-109, L121-124):** `except RuntimeError` blocks

```python
# Before:
except RuntimeError as e:
    user_output(click.style("Error: ", fg="red") + str(e))
    raise SystemExit(1) from e

# After:
except RuntimeError as e:
    raise UserFacingCliError(str(e)) from e
```

### Step 3: Migrate `upgrade_repo` (1 pattern)

**Pattern 5 (L140-145):** `erk_dir.exists()` with multi-line message

```python
# Before:
if not erk_dir.exists():
    user_output(click.style("Error: ", fg="red") + "Not an erk-managed repository")
    user_output(f"The directory {repo.root} does not contain a .erk directory.")
    user_output("This command only works in repositories initialized with erk.")
    raise SystemExit(1)

# After:
Ensure.invariant(
    erk_dir.exists(),
    f"Not an erk-managed repository\n"
    f"The directory {repo.root} does not contain a .erk directory.\n"
    f"This command only works in repositories initialized with erk.",
)
```

### Step 4: Migrate `test_plan_implement_gh_workflow` (3 patterns)

**Pattern 6 (L181-183):** `repo.github is None`

```python
# Before:
if repo.github is None:
    user_output(click.style("Error: ", fg="red") + "Not a GitHub repository")
    raise SystemExit(1)

# After:
Ensure.not_none(repo.github, "Not a GitHub repository")
```

**Pattern 7 (L189-191):** `current_branch is None`

```python
# Before:
current_branch = ctx.git.branch.get_current_branch(repo.root)
if current_branch is None:
    user_output(click.style("Error: ", fg="red") + "Not on a branch (detached HEAD)")
    raise SystemExit(1)

# After:
current_branch = Ensure.not_none(
    ctx.git.branch.get_current_branch(repo.root),
    "Not on a branch (detached HEAD)",
)
```

**Pattern 8 (L257-259):** `username is None`

```python
# Before:
username = ctx.issues.get_current_username()
if username is None:
    user_output(click.style("Error: ", fg="red") + "Not authenticated with GitHub")
    raise SystemExit(1)

# After:
username = Ensure.not_none(
    ctx.issues.get_current_username(),
    "Not authenticated with GitHub",
)
```

## Files Modified

- `src/erk/cli/commands/admin.py` — all 8 pattern migrations

## Test Impact

Existing tests should pass without changes:

- `tests/unit/cli/commands/test_admin_upgrade_repo.py` — checks `exit_code == 1` and `"Not an erk-managed repository" in result.output`, both preserved by `UserFacingCliError`
- `tests/commands/admin/test_github_pr_setting.py` — tests fake behavior only, doesn't exercise error paths
- `tests/commands/admin/test_test_workflow.py` — tests happy path only

The `UserFacingCliError` exception preserves identical behavior: exit code 1, "Error: " prefix in red, message to stderr (visible in `CliRunner` output with default `mix_stderr=True`).

## Verification

1. Run targeted tests: `pytest tests/unit/cli/commands/test_admin_upgrade_repo.py tests/commands/admin/`
2. Run type checker on modified file: `ty check src/erk/cli/commands/admin.py`
3. Run linter: `ruff check src/erk/cli/commands/admin.py`
4. Confirm zero `raise SystemExit(1)` remains in admin.py: `grep "raise SystemExit" src/erk/cli/commands/admin.py`