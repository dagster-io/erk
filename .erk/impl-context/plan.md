# Collapse "impld" and "impling" into "impl"

## Context

The erk dash TUI shows two separate stage labels for the implementation phase: "impling" (actively implementing) and "impld" (implementation complete / PR published). Users find this distinction noisy at the display level — the status emoji column (🚧, 👀, 🚀, 💥) already communicates the substage clearly. Collapsing both to "impl" reduces visual clutter while preserving full behavioral differentiation via color (yellow vs cyan) and the separate "sts" column.

## Approach

Change the display text for both `implementing` and `implemented` stages to `"impl"`, keeping their distinct colors (yellow and cyan respectively). Update the stage-detection logic in `_build_indicators` to use color markup instead of the old text substrings.

## Changes

### 1. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`

**`compute_lifecycle_display` (lines 58–61):** Change display text:
```python
# Before
if stage == "implementing":
    return "[yellow]impling[/yellow]"
if stage == "implemented":
    return "[cyan]impld[/cyan]"

# After
if stage == "implementing":
    return "[yellow]impl[/yellow]"
if stage == "implemented":
    return "[cyan]impl[/cyan]"
```

**`_build_indicators` (lines 196–197):** Update stage detection from text-based to color-based, since both stages now display the same word:
```python
# Before
is_implementing = "impling" in lifecycle_display
is_implemented = "impld" in lifecycle_display

# After
is_implementing = "[yellow]" in lifecycle_display and "impl" in lifecycle_display
is_implemented = "[cyan]" in lifecycle_display and "impl" in lifecycle_display
```

### 2. `tests/unit/plan_store/test_lifecycle_display.py`

Update all assertions and input strings referencing `"[yellow]impling[/yellow]"` → `"[yellow]impl[/yellow]"` and `"[cyan]impld[/cyan]"` → `"[cyan]impl[/cyan]"`.

Affected test assertions (all in this one file):
- `test_implementing_stage_returns_yellow_markup` (line 81)
- `test_implemented_stage_returns_cyan_markup` (line 87)
- `test_infer_review_from_non_draft_open_pr` (line 114)
- `test_inferred_implementing_upgrades_header_with_merged` (line 163)
- All `_format_lifecycle("[yellow]impling[/yellow]", ...)` call sites and expected results (lines ~238–536)
- All `_format_lifecycle("[cyan]impld[/cyan]", ...)` call sites and expected results
- All `_indicators("[yellow]impling[/yellow]", ...)` / `_indicators("[cyan]impld[/cyan]", ...)` call sites
- Workflow run inference assertions (lines ~545–569)

## Verification

```bash
uv run pytest tests/unit/plan_store/test_lifecycle_display.py -v
```

Then run `erk dash` locally to confirm the stage column shows "impl" for both active and completed implementation PRs, with yellow/cyan color differentiation still visible.
