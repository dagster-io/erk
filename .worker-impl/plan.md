# Plan: Add GlobalConfig.test() staticmethod

## Summary

Add a `GlobalConfig.test()` staticmethod that creates a `GlobalConfig` with sensible test defaults, reducing boilerplate across 58 usages in 18 test files.

## Implementation

### Step 1: Add `GlobalConfig.test()` staticmethod

**File:** `src/erk/core/config_store.py:14-27`

Add after the field definitions:

```python
@staticmethod
def test(
    erk_root: Path,
    *,
    use_graphite: bool = True,
    shell_setup_complete: bool = True,
    show_pr_info: bool = True,
    github_planning: bool = True,
) -> "GlobalConfig":
    """Create a GlobalConfig with sensible test defaults."""
    return GlobalConfig(
        erk_root=erk_root,
        use_graphite=use_graphite,
        shell_setup_complete=shell_setup_complete,
        show_pr_info=show_pr_info,
        github_planning=github_planning,
    )
```

**Design decisions:**
- `erk_root` is required (positional) since it's always test-specific (typically `tmp_path / "erks"`)
- All other params are keyword-only with defaults of `True` (most common test scenario)
- `shell_setup_complete=True` default (most tests assume setup is done)

### Step 2: Update test files

Replace verbose `GlobalConfig(...)` calls with `GlobalConfig.test(erk_root)`.

**Files to update (18 files, 58 occurrences):**

| File | Count |
|------|-------|
| `tests/commands/setup/test_init.py` | 20 |
| `tests/unit/cli/test_navigation_helpers.py` | 8 |
| `tests/commands/management/test_impl.py` | 5 |
| `tests/test_utils/env_helpers.py` | 4 |
| `tests/unit/cli/test_navigation_helpers_ensure.py` | 3 |
| `tests/commands/test_status_with_fakes.py` | 2 |
| `tests/commands/display/test_current.py` | 2 |
| `tests/core/foundation/test_context.py` | 2 |
| `tests/unit/status/test_github_pr_collector.py` | 2 |
| `tests/unit/status/test_graphite_stack_collector.py` | 2 |
| Other files (8) | 1 each |

**Transformation pattern:**

```python
# Before
global_config = GlobalConfig(
    erk_root=tmp_path / "erks",
    use_graphite=True,
    shell_setup_complete=True,
    show_pr_info=True,
    github_planning=True,
)

# After
global_config = GlobalConfig.test(tmp_path / "erks")
```

When non-default values are needed:

```python
# Before
global_config = GlobalConfig(
    erk_root=tmp_path / "erks",
    use_graphite=False,  # Non-default
    shell_setup_complete=True,
    show_pr_info=True,
    github_planning=True,
)

# After
global_config = GlobalConfig.test(tmp_path / "erks", use_graphite=False)
```

### Step 3: Run tests

Verify all tests pass after refactoring.

## Notes

- The `tests/commands/AGENTS.md` file contains documentation with a `GlobalConfig(` example - this should also be updated
- The `tests/fakes/context.py` contains a docstring example - should be updated for consistency