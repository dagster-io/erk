# Restore Abbreviated Stage Names in TUI Dashboard

## Context

PR #7790 (`29a811918`) deliberately changed stage display from abbreviated names (`impling`, `impld`) back to full names (`implementing`, `implemented`). The stage column is 9 chars wide, so `implementing` (12 chars) gets truncated to `implement` — losing meaning and looking broken. The abbreviated names were introduced in PR #7646 specifically to fit the 9-char column width.

## Changes

### 1. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`

In `compute_lifecycle_display`:
- Line 58-59: `f"[yellow]{stage}[/yellow]"` → `"[yellow]impling[/yellow]"`
- Line 60-61: `f"[cyan]{stage}[/cyan]"` → `"[cyan]impld[/cyan]"`

In `format_lifecycle_with_status`:
- Line 98: `"implementing" in lifecycle_display` → `"impling" in lifecycle_display`
- Line 119: The early return guard `if not is_implementing and not is_review:` — also need to restore `is_implemented` detection for `"impld"` so conflict indicators work on that stage too

### 2. `tests/unit/plan_store/test_lifecycle_display.py`

Update all assertions that check for `implementing`/`implemented` display strings:
- `"[yellow]implementing[/yellow]"` → `"[yellow]impling[/yellow]"`
- `"[cyan]implemented[/cyan]"` → `"[cyan]impld[/cyan]"`
- Status-decorated variants: `"[yellow]🚧 implementing[/yellow]"` → `"[yellow]🚧 impling[/yellow]"`, etc.

## Verification

- Run `uv run pytest tests/unit/plan_store/test_lifecycle_display.py` — all pass
- Run `uv run pytest tests/tui/test_plan_table.py` — all pass
- Visual check: `erk dash -i` shows `impling`/`impld` fitting cleanly in stage column
