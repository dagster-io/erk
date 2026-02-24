# Plan: Move `erk plan list` to `erk pr list` with `--stage` filter

**Part of Objective #7978, Node 3.1**

## Context

Objective #7978 unifies CLI commands under `erk pr`. Phase 2 (PR #8010) moved close/view/log/replan. This node moves `plan list` → `pr list` and adds a `--stage` lifecycle filter. The `dash` command remains top-level but its import path must update after the file moves.

## Implementation Steps

### 1. Move file: `list_cmd.py` from plan/ to pr/

- **Source:** `src/erk/cli/commands/plan/list_cmd.py`
- **Destination:** `src/erk/cli/commands/pr/list_cmd.py`
- Physical `git mv` (not copy)

### 2. Rename functions to follow pr group convention

In the moved `src/erk/cli/commands/pr/list_cmd.py`:
- `list_plans()` → `pr_list()`
- `_list_plans_impl()` → `_pr_list_impl()`
- `plan_filter_options()` → `pr_filter_options()` (since it's shared between list and dash)
- Update all docstrings/examples: `erk plan list` → `erk pr list`
- Update `dash()` docstring: `erk plan list` → `erk pr list`
- Keep `dash()` name (it's a top-level command, not renamed)

### 3. Add `--stage` CLI option

In `pr_filter_options()` (the renamed decorator), add:
```python
f = click.option(
    "--stage",
    type=click.Choice(
        ["prompted", "planning", "planned", "impl", "merged", "closed"],
        case_sensitive=False,
    ),
    help="Filter by lifecycle stage",
)(f)
```

Add `stage: str | None` parameter to `pr_list()`, `_pr_list_impl()`, `dash()`, and `_run_interactive_mode()`.

### 4. Add `lifecycle_stage` field to `PlanFilters`

**File:** `src/erk/tui/data/types.py`

Add to `PlanFilters`:
```python
lifecycle_stage: str | None = None
```

Update the docstring to document it.

### 5. Implement `--stage` post-fetch filtering

In `_pr_list_impl()`, after `rows = provider.fetch_plans(filters)`, add:
```python
if stage is not None:
    rows = [r for r in rows if strip_rich_markup(r.lifecycle_display).startswith(stage)]
```

`strip_rich_markup` is already imported. This handles Rich markup and status indicator suffixes (e.g., `"impl 🚧"` matches `"impl"`).

For `_run_interactive_mode()`, pass `lifecycle_stage=stage` to `PlanFilters` constructor. The TUI doesn't filter on it yet (future work) but it's stored for when it does.

### 6. Update pr group registration

**File:** `src/erk/cli/commands/pr/__init__.py`

Add:
```python
from erk.cli.commands.pr.list_cmd import pr_list
# ...
pr_group.add_command(pr_list, name="list")
```

### 7. Remove from plan group

**File:** `src/erk/cli/commands/plan/__init__.py`

Remove:
```python
from erk.cli.commands.plan.list_cmd import list_plans
# ...
plan_group.add_command(list_plans, name="list")
```

### 8. Update dash import in cli.py

**File:** `src/erk/cli/cli.py`

Change:
```python
from erk.cli.commands.plan.list_cmd import dash
```
to:
```python
from erk.cli.commands.pr.list_cmd import dash
```

### 9. Move and update tests

- **Source:** `tests/commands/plan/test_list.py`
- **Destination:** `tests/commands/pr/test_list.py`
- `git mv` the file
- Update all CLI invocations: `["plan", "list", ...]` → `["pr", "list", ...]`
- Update module docstring
- Add a test for `--stage` filtering (e.g., two plans with different lifecycle stages, verify `--stage planned` returns only the matching one)

### 10. Update AGENTS.md reference

**File:** `AGENTS.md` line 114

Change: `erk plan list — view open plans` → `erk pr list — view open plans`

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/plan/list_cmd.py` | Delete (git mv) |
| `src/erk/cli/commands/pr/list_cmd.py` | New (moved from plan/) |
| `src/erk/cli/commands/pr/__init__.py` | Add pr_list registration |
| `src/erk/cli/commands/plan/__init__.py` | Remove list_plans |
| `src/erk/cli/cli.py` | Update dash import path |
| `src/erk/tui/data/types.py` | Add lifecycle_stage to PlanFilters |
| `tests/commands/plan/test_list.py` | Delete (git mv) |
| `tests/commands/pr/test_list.py` | New (moved from plan/), update invocations |
| `AGENTS.md` | Update "plan list" reference |

## Verification

1. Run existing tests (now at new location): `pytest tests/commands/pr/test_list.py`
2. Run `erk pr list` — should show plans
3. Run `erk pr list --stage impl` — should filter to impl-stage plans only
4. Run `erk dash` — should still work (top-level command unchanged)
5. Run `erk plan list` — should fail (command removed)
6. Run `ty` for type checking
7. Run `ruff` for linting
